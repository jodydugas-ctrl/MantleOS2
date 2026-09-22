from __future__ import annotations

"""Read-only uncertainty challenger for unresolved SCAN coverage.

The challenger does not grade, promote, or mutate evidence. It interrogates the
existing gap queue and canonical graph for nearby evidence that deserves a
mechanical recheck. Any later state change must come from SCAN itself.
"""

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .coverage_report import build_coverage_report

CHALLENGE_SCHEMA = "scan-uncertainty-challenges/0.1"


def _decode(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _evidence_ids(row: dict[str, Any] | None) -> list[str]:
    if not row:
        return []
    value = row.get("evidence_ids")
    if not isinstance(value, list):
        value = _decode(row.get("evidence_ids_json"), [])
    return sorted({str(x) for x in value if x}) if isinstance(value, list) else []


def _challenge_id(gap_id: str, kind: str) -> str:
    return sha256(f"{gap_id}\0{kind}".encode("utf-8", "surrogatepass")).hexdigest()[:24]


def _policy_for_gap(gap: dict[str, Any]) -> tuple[str, list[str], str]:
    category = str(gap.get("category") or "")
    reason = str(gap.get("reason_code") or "")
    state = str(gap.get("state") or "UNKNOWN").upper()

    if category == "acquisition" or reason == "CONTENT_UNAVAILABLE":
        return (
            "BLOCKED_ON_ACQUISITION",
            ["ACQUIRE_VERIFIED_BYTES", "VERIFY_SPECIMEN_IDENTITY", "RERUN_AFFECTED_ADAPTERS"],
            "Can verified bytes be acquired for the accounted path without changing specimen identity?",
        )
    if category == "file-coverage" or "PARSER" in reason:
        return (
            "PARSER_COVERAGE_REQUIRED",
            ["VERIFY_PARSER_FAILURE_OR_BUDGET", "RERUN_RELEVANT_ADAPTER", "REBUILD_DERIVED_PROJECTIONS"],
            "Can deterministic parser or adapter coverage resolve this file-level uncertainty?",
        )
    if category == "surface-closure":
        return (
            "RECHECK_SURFACE_ROUTE",
            ["TRACE_INCIDENT_ROUTING_EDGES", "RECOMPUTE_SURFACE_CLOSURE", "VERIFY_HANDLER_EVIDENCE"],
            "Does existing local graph evidence contain an overlooked route from this surface to a handler?",
        )
    if category == "effect-closure":
        return (
            "RECHECK_EFFECT_ROUTE",
            ["TRACE_EFFECT_NEIGHBORHOOD", "RECOMPUTE_EFFECT_CLOSURE", "VERIFY_TERMINAL_EVIDENCE"],
            "Does existing local graph evidence contain an overlooked route to state, effect, boundary, or feedback?",
        )
    if category == "completeness":
        return (
            "RECHECK_COMPLETENESS_DEPENDENCIES",
            ["VERIFY_COMPLETENESS_EVIDENCE", "REQUERY_SUPPORT_RELATIONS", "RECOMPUTE_COMPLETENESS"],
            "Do existing evidence dependencies justify a different completeness state?",
        )
    if category in {"node-coverage", "edge-coverage"}:
        return (
            "RECHECK_LOCAL_GRAPH",
            ["VERIFY_DIRECT_EVIDENCE", "TRACE_ONE_HOP_NEIGHBORHOOD", "RERUN_RELEVANT_ADAPTER"],
            "Is there existing graph or evidence support that the original extraction did not fully join?",
        )
    if category == "finding":
        return (
            "REVIEW_RECORDED_FINDING",
            ["VERIFY_FINDING_EVIDENCE", "TRACE_RELATED_OBJECTS", "RERUN_TARGETED_MECHANICAL_CHECK"],
            "Can this recorded finding be further bounded or resolved using existing mechanical evidence?",
        )
    return (
        "RECHECK_LOCAL_GRAPH",
        ["VERIFY_DIRECT_EVIDENCE", "TRACE_ONE_HOP_NEIGHBORHOOD"],
        f"Can existing mechanical evidence reduce this {state} uncertainty without semantic guessing?",
    )


def build_uncertainty_challenges(
    store,
    *,
    engine_version: str,
    coverage_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    coverage_report = coverage_report or build_coverage_report(store, engine_version=engine_version)
    gaps = list((coverage_report.get("gaps") or {}).get("records") or [])

    nodes = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,kind,name,path,coverage,evidence_ids_json FROM nodes ORDER BY id"
        )
    }
    edges = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,src,dst,kind,coverage,evidence_ids_json FROM edges ORDER BY id"
        )
    }
    findings = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,kind,title,status,evidence_ids_json FROM findings ORDER BY id"
        )
    }
    completeness = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,key,label,state,evidence_ids_json FROM completeness_dimensions ORDER BY id"
        )
    }
    semantic_objects = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,object_type,subtype,label,coverage FROM semantic_objects ORDER BY id"
        )
    }
    semantic_relations = store.query(
        "SELECT id,src,dst,kind,status,evidence_ids_json FROM semantic_relations ORDER BY id"
    )
    evidence = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,file_id,path,start_line,end_line,evidence_class,extractor FROM evidence ORDER BY id"
        )
    }

    incident_edges: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in edges.values():
        incident_edges[str(row["src"])].append(row)
        incident_edges[str(row["dst"])].append(row)

    incident_semantic: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in semantic_relations:
        incident_semantic[str(row["src"])].append(row)
        incident_semantic[str(row["dst"])].append(row)

    challenges: list[dict[str, Any]] = []
    for gap in gaps:
        object_id = str(gap.get("object_id") or "")
        kind, checks, question = _policy_for_gap(gap)
        candidate_evidence = set(str(x) for x in gap.get("evidence_ids") or [])
        neighbor_ids: set[str] = set()
        mapped_neighbor_ids: set[str] = set()
        relation_ids: set[str] = set()

        direct_row = nodes.get(object_id) or edges.get(object_id) or findings.get(object_id) or completeness.get(object_id)
        candidate_evidence.update(_evidence_ids(direct_row))

        for edge in incident_edges.get(object_id, []):
            relation_ids.add(str(edge["id"]))
            candidate_evidence.update(_evidence_ids(edge))
            other = str(edge["dst"]) if str(edge["src"]) == object_id else str(edge["src"])
            neighbor_ids.add(other)
            node = nodes.get(other)
            if node:
                candidate_evidence.update(_evidence_ids(node))
                if str(node.get("coverage") or "UNKNOWN").upper() == "MAPPED":
                    mapped_neighbor_ids.add(other)

        if object_id in edges:
            edge = edges[object_id]
            for endpoint in (str(edge["src"]), str(edge["dst"])):
                neighbor_ids.add(endpoint)
                node = nodes.get(endpoint)
                if node:
                    candidate_evidence.update(_evidence_ids(node))
                    if str(node.get("coverage") or "UNKNOWN").upper() == "MAPPED":
                        mapped_neighbor_ids.add(endpoint)

        for rel in incident_semantic.get(object_id, []):
            relation_ids.add(str(rel["id"]))
            candidate_evidence.update(_evidence_ids(rel))
            other = str(rel["dst"]) if str(rel["src"]) == object_id else str(rel["src"])
            neighbor_ids.add(other)
            obj = semantic_objects.get(other)
            if obj and str(obj.get("coverage") or "UNKNOWN").upper() == "MAPPED":
                mapped_neighbor_ids.add(other)

        candidate_evidence = {eid for eid in candidate_evidence if eid in evidence}

        if kind == "BLOCKED_ON_ACQUISITION":
            disposition = "EXTERNAL_INPUT_REQUIRED"
        elif kind == "PARSER_COVERAGE_REQUIRED":
            disposition = "SCANNER_WORK_REQUIRED"
        elif candidate_evidence or mapped_neighbor_ids:
            disposition = "MECHANICAL_RECHECK_AVAILABLE"
        else:
            disposition = "NO_LOCAL_SUPPORT_FOUND"

        challenges.append({
            "challenge_id": _challenge_id(str(gap.get("gap_id") or object_id), kind),
            "gap_id": str(gap.get("gap_id") or ""),
            "object_id": object_id,
            "source_state": str(gap.get("state") or "UNKNOWN").upper(),
            "gap_category": str(gap.get("category") or ""),
            "challenge_kind": kind,
            "disposition": disposition,
            "question": question,
            "candidate_evidence_ids": sorted(candidate_evidence),
            "candidate_neighbor_ids": sorted(neighbor_ids),
            "mapped_neighbor_ids": sorted(mapped_neighbor_ids),
            "incident_relation_ids": sorted(relation_ids),
            "mechanical_checks": checks,
            "canonical_write_allowed": False,
            "promotion_allowed": False,
        })

    challenges.sort(key=lambda row: (row["challenge_kind"], row["gap_id"], row["challenge_id"]))
    by_kind = Counter(row["challenge_kind"] for row in challenges)
    by_disposition = Counter(row["disposition"] for row in challenges)
    return {
        "schema_version": CHALLENGE_SCHEMA,
        "engine_version": engine_version,
        "authority": {
            "canonical_store": "scan_index.sqlite",
            "projection_only": True,
            "canonical_write_allowed": False,
            "promotion_allowed": False,
            "state_change_requires_mechanical_rescan_or_existing_promotion_gate": True,
            "llm_required": False,
        },
        "source_gap_schema": (coverage_report.get("gaps") or {}).get("schema_version"),
        "challenge_count": len(challenges),
        "by_kind": dict(sorted(by_kind.items())),
        "by_disposition": dict(sorted(by_disposition.items())),
        "challenges": challenges,
    }


def render_uncertainty_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCAN Uncertainty Challenger",
        "",
        f"Schema: {report['schema_version']}",
        f"Challenges: {report['challenge_count']}",
        "",
        "This is a read-only adversarial review of unresolved evidence states. It cannot promote or rewrite canonical evidence.",
        "",
        f"By kind: {json.dumps(report['by_kind'], sort_keys=True)}",
        f"By disposition: {json.dumps(report['by_disposition'], sort_keys=True)}",
        "",
    ]
    if not report["challenges"]:
        return "\n".join(lines + ["No unresolved gaps required challenge review.", ""])

    lines += [
        "| Gap | State | Challenge | Disposition | Candidate evidence | Mechanical checks |",
        "|---|---|---|---|---|---|",
    ]
    for row in report["challenges"]:
        ev = ", ".join(row["candidate_evidence_ids"]) or "none"
        checks = ", ".join(row["mechanical_checks"])
        lines.append(
            f"| {row['gap_id']} | {row['source_state']} | {row['challenge_kind']} | "
            f"{row['disposition']} | {ev} | {checks} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_uncertainty_outputs(
    store,
    output: Path,
    *,
    engine_version: str,
    coverage_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_uncertainty_challenges(
        store, engine_version=engine_version, coverage_report=coverage_report,
    )
    json_path = output / "uncertainty_challenges.json"
    md_path = output / "uncertainty_challenges.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_uncertainty_markdown(report), encoding="utf-8")
    return {
        "schema_version": CHALLENGE_SCHEMA,
        "state": "PASS",
        "challenge_count": report["challenge_count"],
        "by_disposition": report["by_disposition"],
        "files": [json_path.name, md_path.name],
    }
