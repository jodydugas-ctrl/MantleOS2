from __future__ import annotations

"""Explicit provenance layers over the existing canonical semantic graph.

No duplicate graph is created. This module classifies canonical objects/relations,
preserves each object's own coverage state, and exposes support lineage across E0-E4.
"""

from collections import Counter, defaultdict, deque
import json
from pathlib import Path
from typing import Any

LAYER_SCHEMA = "scan-layered-provenance/0.1"

LAYER_DEFS = {
    "E0": {"name": "source-evidence", "ordinal": 0, "canonical": True},
    "E1": {"name": "mechanical-anatomy", "ordinal": 1, "canonical": True},
    "E2": {"name": "semantic-interpretation", "ordinal": 2, "canonical": True},
    "E3": {"name": "reconstruction-contract", "ordinal": 3, "canonical": True},
    "E4": {"name": "human-description", "ordinal": 4, "canonical": False},
}
OBJECT_LAYER = {
    "SPECIMEN": "E0",
    "FILE": "E0",
    "EVIDENCE": "E0",
    "ANATOMICAL_OBJECT": "E1",
    "GRAPH_RELATION": "E1",
    "FINDING": "E1",
    "INTERPRETATION": "E2",
    "BEHAVIOR": "E2",
    "RECONSTRUCTION_ANCHOR": "E3",
    "HUMAN_DESCRIPTION": "E4",
}
PROOF_KINDS = {"contains_evidence", "supports", "derived_from", "supports_anchor"}
NON_PROOF_KINDS = {"contradicts"}


def _layer_for(object_type: str) -> str:
    return OBJECT_LAYER.get(str(object_type), "UNCLASSIFIED")


def build_layered_provenance(store, *, engine_version: str) -> dict[str, Any]:
    objects = {str(o["id"]): dict(o) for o in store.semantic_objects()}
    relations = [dict(r) for r in store.semantic_relations()]

    incoming: dict[str, list[dict[str, Any]]] = defaultdict(list)
    outgoing: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for rel in relations:
        incoming[str(rel["dst"])].append(rel)
        outgoing[str(rel["src"])].append(rel)

    def lineage(object_id: str) -> dict[str, Any]:
        start = objects[object_id]
        start_layer = _layer_for(start.get("object_type"))
        immediate = []
        lower = []
        contradictions = []
        evidence_ids: set[str] = set()
        file_ids: set[str] = set()
        specimen_ids: set[str] = set()

        for rel in incoming.get(object_id, []):
            src = str(rel["src"])
            if rel.get("kind") in NON_PROOF_KINDS:
                contradictions.append(str(rel["id"]))
            if rel.get("kind") not in PROOF_KINDS:
                continue
            immediate.append(src)
            src_obj = objects.get(src)
            if src_obj:
                src_layer = _layer_for(src_obj.get("object_type"))
                if src_layer in LAYER_DEFS and start_layer in LAYER_DEFS:
                    if LAYER_DEFS[src_layer]["ordinal"] < LAYER_DEFS[start_layer]["ordinal"]:
                        lower.append(src)

        visited = {object_id}
        queue = deque([(object_id, 0)])
        while queue:
            current, depth = queue.popleft()
            if depth >= 16:
                continue
            for rel in incoming.get(current, []):
                if rel.get("kind") not in PROOF_KINDS:
                    continue
                src = str(rel["src"])
                obj = objects.get(src)
                if obj:
                    typ = str(obj.get("object_type"))
                    if typ == "EVIDENCE":
                        evidence_ids.add(src)
                    elif typ == "FILE":
                        file_ids.add(src)
                    elif typ == "SPECIMEN":
                        specimen_ids.add(src)
                if src not in visited:
                    visited.add(src)
                    queue.append((src, depth + 1))

        if start.get("object_type") == "EVIDENCE":
            evidence_ids.add(object_id)
        if start.get("object_type") == "FILE":
            file_ids.add(object_id)
        if start.get("object_type") == "SPECIMEN":
            specimen_ids.add(object_id)

        return {
            "immediate_support_ids": sorted(set(immediate)),
            "lower_layer_support_ids": sorted(set(lower)),
            "evidence_ids": sorted(evidence_ids),
            "source_file_ids": sorted(file_ids),
            "specimen_ids": sorted(specimen_ids),
            "contradiction_relation_ids": sorted(set(contradictions)),
            "proof_complete_to_e0": bool(evidence_ids or start.get("object_type") in {"SPECIMEN", "FILE"}),
        }

    records = []
    layer_counts: dict[str, Counter] = defaultdict(Counter)
    unclassified_types = Counter()
    for object_id in sorted(objects):
        obj = objects[object_id]
        layer = _layer_for(obj.get("object_type"))
        coverage = str(obj.get("coverage") or "UNKNOWN").upper()
        if layer in LAYER_DEFS:
            layer_counts[layer][coverage] += 1
        else:
            unclassified_types[str(obj.get("object_type") or "UNKNOWN")] += 1
        rec = {
            "object_id": object_id,
            "object_type": obj.get("object_type"),
            "subtype": obj.get("subtype"),
            "label": obj.get("label"),
            "layer": layer,
            "layer_name": LAYER_DEFS.get(layer, {}).get("name", "unclassified"),
            "coverage": coverage,
            "presentation_only": layer == "E4",
            "lineage": lineage(object_id),
        }
        records.append(rec)

    relation_records = []
    transition_counts = Counter()
    for rel in sorted(relations, key=lambda x: str(x["id"])):
        src_layer = _layer_for(objects.get(str(rel["src"]), {}).get("object_type"))
        dst_layer = _layer_for(objects.get(str(rel["dst"]), {}).get("object_type"))
        if src_layer in LAYER_DEFS and dst_layer in LAYER_DEFS:
            a = LAYER_DEFS[src_layer]["ordinal"]
            b = LAYER_DEFS[dst_layer]["ordinal"]
            direction = "FORWARD" if a < b else "WITHIN_LAYER" if a == b else "BACKWARD"
        else:
            direction = "UNCLASSIFIED"
        transition_counts[direction] += 1
        relation_records.append({
            "relation_id": str(rel["id"]),
            "kind": rel.get("kind"),
            "status": str(rel.get("status") or "UNKNOWN").upper(),
            "src": str(rel["src"]),
            "dst": str(rel["dst"]),
            "src_layer": src_layer,
            "dst_layer": dst_layer,
            "layer_direction": direction,
            "proof_relation": rel.get("kind") in PROOF_KINDS,
        })

    layers = {}
    for layer, meta in LAYER_DEFS.items():
        counts = layer_counts.get(layer, Counter())
        layers[layer] = {
            **meta,
            "object_count": sum(counts.values()),
            "coverage_states": dict(sorted(counts.items())),
        }

    return {
        "schema_version": LAYER_SCHEMA,
        "engine_version": engine_version,
        "authority": {
            "canonical_store": "scan_index.sqlite",
            "projection_only": True,
            "duplicates_canonical_graph": False,
            "canonical_write_allowed": False,
            "coverage_preserved_per_object": True,
            "higher_layer_text_does_not_upgrade_lower_layer_evidence": True,
        },
        "layer_model": layers,
        "object_count": len(records),
        "relation_count": len(relation_records),
        "unclassified_object_types": dict(sorted(unclassified_types.items())),
        "transition_counts": dict(sorted(transition_counts.items())),
        "objects": records,
        "relations": relation_records,
    }


def render_layered_provenance_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCAN Layered Provenance",
        "",
        f"Schema: {report['schema_version']}",
        "",
        "E0 source/evidence -> E1 mechanical anatomy -> E2 semantic interpretation -> E3 reconstruction contract -> E4 human description.",
        "",
        "Coverage is preserved independently at every layer. A MAPPED lower-layer fact does not force a higher-layer interpretation to be MAPPED.",
        "",
        "| Layer | Meaning | Objects | Coverage states | Canonical |",
        "|---|---|---:|---|---|",
    ]
    for layer in ("E0", "E1", "E2", "E3", "E4"):
        row = report["layer_model"][layer]
        lines.append(
            f"| {layer} | {row['name']} | {row['object_count']} | "
            f"{json.dumps(row['coverage_states'], sort_keys=True)} | {row['canonical']} |"
        )
    if report["unclassified_object_types"]:
        lines += ["", f"Unclassified object types: {json.dumps(report['unclassified_object_types'], sort_keys=True)}"]
    lines += [
        "",
        "E4 is presentation-only by design. Human prose may cite lower-layer IDs but does not become source evidence.",
        "",
    ]
    return "\n".join(lines)


def write_layered_provenance_outputs(store, output: Path, *, engine_version: str) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_layered_provenance(store, engine_version=engine_version)
    (output / "layered_provenance.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "layered_provenance.md").write_text(
        render_layered_provenance_markdown(report), encoding="utf-8"
    )
    return {
        "schema_version": LAYER_SCHEMA,
        "state": "PASS",
        "object_count": report["object_count"],
        "relation_count": report["relation_count"],
        "unclassified_object_types": report["unclassified_object_types"],
        "files": ["layered_provenance.json", "layered_provenance.md"],
    }
