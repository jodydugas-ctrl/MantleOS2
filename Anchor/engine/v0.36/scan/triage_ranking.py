from __future__ import annotations

"""Deterministic investigation-priority ranking for unresolved SCAN gaps.

Ranking is operational triage only. A high score means "investigate sooner",
never "more true", "more confident", or "eligible for promotion".
"""

from collections import Counter, defaultdict, deque
import json
from pathlib import Path
from typing import Any

from .coverage_report import build_coverage_report
from .uncertainty_challenger import build_uncertainty_challenges

TRIAGE_SCHEMA = "scan-triage-ranking/0.1"

TRAVERSAL_KINDS = {
    "resolves_to", "alternate_route_to", "emits", "dispatches_to", "invokes",
    "triggers", "triggers_async", "delivers_async_to", "routes_to", "handled_in",
    "calls", "produces_effect", "changes_state", "crosses_boundary", "opens_surface",
    "produces_feedback", "has_effect", "has_feedback", "reaches_extension",
}
ROUTING_KINDS = {
    "resolves_to", "alternate_route_to", "emits", "dispatches_to", "invokes",
    "triggers", "routes_to", "opens_surface",
}
TERMINAL_KINDS = {
    "effect", "state_change", "nest_boundary", "extension_receptor_candidate",
    "extension_receptor", "capability_factory", "persistence_operation",
    "error_path", "feedback",
}
PROOF_RELATIONS = {"contains_evidence", "supports", "derived_from", "supports_anchor"}

COMPONENT_MAX = {
    "structural_connectivity": 20,
    "human_surface_reach": 30,
    "effect_terminal_reach": 20,
    "reconstruction_anchor_dependency": 20,
    "mechanical_recheck_support": 10,
}


def _decode(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _actionable_surface(row: dict[str, Any]) -> bool:
    if row.get("kind") not in {"human_surface", "surface_reference", "surface_factory_output"}:
        return False
    attrs = _decode(row.get("attributes_json"), {})
    return attrs.get("surface_role") != "presented"


def _bounded_reachable(
    starts: set[str],
    adjacency: dict[str, list[str]],
    *,
    max_depth: int,
) -> set[str]:
    visited = set(starts)
    queue = deque((node, 0) for node in sorted(starts))
    while queue:
        current, depth = queue.popleft()
        if depth >= max_depth:
            continue
        for nxt in adjacency.get(current, []):
            if nxt in visited:
                continue
            visited.add(nxt)
            queue.append((nxt, depth + 1))
    return visited


def build_triage_ranking(
    store,
    *,
    engine_version: str,
    coverage_report: dict[str, Any] | None = None,
    challenge_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    coverage_report = coverage_report or build_coverage_report(store, engine_version=engine_version)
    challenge_report = challenge_report or build_uncertainty_challenges(
        store, engine_version=engine_version, coverage_report=coverage_report,
    )

    nodes_list = store.query(
        "SELECT id,file_id,kind,name,path,coverage,attributes_json FROM nodes ORDER BY id"
    )
    nodes = {str(row["id"]): row for row in nodes_list}
    edges_list = store.query(
        "SELECT id,src,dst,kind,coverage FROM edges ORDER BY id"
    )
    edges = {str(row["id"]): row for row in edges_list}
    semantic_objects = {
        str(row["id"]): row
        for row in store.query(
            "SELECT id,object_type,subtype,label,coverage FROM semantic_objects ORDER BY id"
        )
    }
    semantic_relations = store.query(
        "SELECT id,src,dst,kind,status FROM semantic_relations ORDER BY id"
    )

    outgoing: dict[str, list[str]] = defaultdict(list)
    reverse: dict[str, list[str]] = defaultdict(list)
    degree: Counter = Counter()
    for edge in edges_list:
        src, dst = str(edge["src"]), str(edge["dst"])
        degree[src] += 1
        degree[dst] += 1
        if str(edge["kind"]) in TRAVERSAL_KINDS:
            outgoing[src].append(dst)
        if str(edge["kind"]) in ROUTING_KINDS:
            reverse[dst].append(src)

    for values in outgoing.values():
        values.sort()
    for values in reverse.values():
        values.sort()

    nodes_by_file: dict[str, set[str]] = defaultdict(set)
    for row in nodes_list:
        if row.get("file_id"):
            nodes_by_file[str(row["file_id"])].add(str(row["id"]))

    actionable_surfaces = {str(row["id"]) for row in nodes_list if _actionable_surface(row)}
    terminal_nodes = {str(row["id"]) for row in nodes_list if row.get("kind") in TERMINAL_KINDS}

    sem_out: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for rel in semantic_relations:
        if str(rel.get("kind")) in PROOF_RELATIONS:
            sem_out[str(rel["src"])].append((str(rel["dst"]), str(rel["kind"])))
    for values in sem_out.values():
        values.sort()

    anchors = {
        object_id for object_id, row in semantic_objects.items()
        if row.get("object_type") == "RECONSTRUCTION_ANCHOR"
    }

    challenge_by_gap = {
        str(row["gap_id"]): row for row in challenge_report.get("challenges") or []
    }
    gaps = list((coverage_report.get("gaps") or {}).get("records") or [])
    rows: list[dict[str, Any]] = []

    for gap in gaps:
        gap_id = str(gap["gap_id"])
        object_id = str(gap.get("object_id") or "")
        challenge = challenge_by_gap.get(gap_id, {})

        physical_targets: set[str] = set()
        if object_id in nodes:
            physical_targets.add(object_id)
        elif object_id in edges:
            physical_targets.update((str(edges[object_id]["src"]), str(edges[object_id]["dst"])))
        elif object_id in nodes_by_file:
            physical_targets.update(nodes_by_file[object_id])

        connectivity_raw = sum(degree[target] for target in physical_targets)
        connectivity_component = min(20, connectivity_raw * 2)

        surface_ids: set[str] = set()
        if physical_targets:
            ancestors = _bounded_reachable(physical_targets, reverse, max_depth=8)
            surface_ids = actionable_surfaces & ancestors
        human_component = min(30, len(surface_ids) * 10)

        terminal_ids: set[str] = set()
        if physical_targets:
            descendants = _bounded_reachable(physical_targets, outgoing, max_depth=8)
            terminal_ids = terminal_nodes & descendants
        effect_component = min(20, len(terminal_ids) * 5)

        anchor_ids: set[str] = set()
        if object_id in semantic_objects:
            visited = {object_id}
            queue = deque([(object_id, 0)])
            while queue:
                current, depth = queue.popleft()
                if depth >= 8:
                    continue
                for nxt, _kind in sem_out.get(current, []):
                    if nxt in anchors:
                        anchor_ids.add(nxt)
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append((nxt, depth + 1))
        anchor_component = min(20, len(anchor_ids) * 10)

        disposition = str(challenge.get("disposition") or "NO_CHALLENGE")
        support_component = 10 if disposition == "MECHANICAL_RECHECK_AVAILABLE" else 5 if disposition == "SCANNER_WORK_REQUIRED" else 0

        components = {
            "structural_connectivity": connectivity_component,
            "human_surface_reach": human_component,
            "effect_terminal_reach": effect_component,
            "reconstruction_anchor_dependency": anchor_component,
            "mechanical_recheck_support": support_component,
        }
        score = sum(components.values())
        rows.append({
            "gap_id": gap_id,
            "object_id": object_id,
            "gap_category": gap.get("category"),
            "source_state": gap.get("state"),
            "label": gap.get("label"),
            "path": gap.get("path"),
            "challenge_kind": challenge.get("challenge_kind"),
            "challenge_disposition": disposition,
            "investigation_score": score,
            "components": components,
            "raw_signals": {
                "incident_edge_degree": connectivity_raw,
                "reachable_actionable_surface_count": len(surface_ids),
                "reachable_actionable_surface_ids": sorted(surface_ids),
                "reachable_terminal_count": len(terminal_ids),
                "reachable_terminal_ids": sorted(terminal_ids),
                "reconstruction_anchor_count": len(anchor_ids),
                "reconstruction_anchor_ids": sorted(anchor_ids),
            },
            "importance_only": True,
            "confidence_effect": "NONE",
            "promotion_effect": "NONE",
            "canonical_write_allowed": False,
        })

    rows.sort(key=lambda row: (-row["investigation_score"], str(row["gap_id"])))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index

    buckets = Counter(
        "HIGH" if row["investigation_score"] >= 60
        else "MEDIUM" if row["investigation_score"] >= 30
        else "LOW"
        for row in rows
    )
    return {
        "schema_version": TRIAGE_SCHEMA,
        "engine_version": engine_version,
        "authority": {
            "canonical_store": "scan_index.sqlite",
            "projection_only": True,
            "importance_not_truth": True,
            "confidence_effect": "NONE",
            "promotion_effect": "NONE",
            "canonical_write_allowed": False,
            "llm_required": False,
        },
        "component_max": dict(COMPONENT_MAX),
        "ranking_policy": {
            "maximum_score": sum(COMPONENT_MAX.values()),
            "tie_breaker": "gap_id ascending",
            "state_used_as_weight": False,
            "category_used_as_weight": False,
        },
        "ranked_count": len(rows),
        "buckets": dict(sorted(buckets.items())),
        "rankings": rows,
    }


def render_triage_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCAN Investigation Triage",
        "",
        f"Schema: {report['schema_version']}",
        f"Ranked gaps: {report['ranked_count']}",
        "",
        "This ordering estimates investigation leverage only. It does not change evidence, confidence, coverage, or promotion eligibility.",
        "",
        "| Rank | Score | Gap | State | Category | Surface reach | Effect reach | Anchors | Challenger |",
        "|---:|---:|---|---|---|---:|---:|---:|---|",
    ]
    for row in report["rankings"]:
        raw = row["raw_signals"]
        lines.append(
            f"| {row['rank']} | {row['investigation_score']} | {row['gap_id']} | "
            f"{row.get('source_state') or ''} | {row.get('gap_category') or ''} | "
            f"{raw['reachable_actionable_surface_count']} | {raw['reachable_terminal_count']} | "
            f"{raw['reconstruction_anchor_count']} | {row.get('challenge_disposition') or ''} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_triage_outputs(
    store,
    output: Path,
    *,
    engine_version: str,
    coverage_report: dict[str, Any] | None = None,
    challenge_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_triage_ranking(
        store,
        engine_version=engine_version,
        coverage_report=coverage_report,
        challenge_report=challenge_report,
    )
    json_path = output / "triage_ranking.json"
    md_path = output / "triage_ranking.md"
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_triage_markdown(report), encoding="utf-8")
    return {
        "schema_version": TRIAGE_SCHEMA,
        "state": "PASS",
        "ranked_count": report["ranked_count"],
        "buckets": report["buckets"],
        "files": [json_path.name, md_path.name],
    }
