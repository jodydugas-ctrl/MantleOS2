from __future__ import annotations

from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from .integrity import effect_closure, surface_closure

COVERAGE_REPORT_SCHEMA = "scan-coverage-report/0.1"
GAPS_SCHEMA = "scan-gaps/0.1"
UNRESOLVED_STATES = {"PARTIAL", "UNKNOWN", "BLOCKED"}
NON_GAP_COMPLETENESS = {"MAPPED", "NOT_APPLICABLE"}


def _decode(value: Any, default: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _attrs(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("attributes")
    if isinstance(value, dict):
        return value
    parsed = _decode(row.get("attributes_json"), {})
    return parsed if isinstance(parsed, dict) else {}


def _evidence_ids(row: dict[str, Any]) -> list[str]:
    value = row.get("evidence_ids")
    if not isinstance(value, list):
        value = _decode(row.get("evidence_ids_json"), [])
    return sorted({str(x) for x in value if x}) if isinstance(value, list) else []


def _state_counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field) or "UNKNOWN").upper() for row in rows).items()))


def _grouped_state_counts(rows: list[dict[str, Any]], group: str, state: str) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        grouped[str(row.get(group) or "unknown")][str(row.get(state) or "UNKNOWN").upper()] += 1
    return {key: dict(sorted(value.items())) for key, value in sorted(grouped.items())}


def _gap(
    category: str,
    object_id: str,
    state: str,
    reason_code: str,
    label: str,
    resolution_target: str,
    *,
    path: str | None = None,
    object_kind: str | None = None,
    evidence_ids: list[str] | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    state = str(state or "UNKNOWN").upper()
    seed = "\0".join((category, object_id, state, reason_code))
    return {
        "gap_id": sha256(seed.encode("utf-8", "surrogatepass")).hexdigest()[:24],
        "category": category,
        "object_id": object_id,
        "object_kind": object_kind,
        "label": label,
        "path": path,
        "state": state,
        "reason_code": reason_code,
        "detail": detail,
        "evidence_ids": sorted(set(evidence_ids or [])),
        "resolution_target": resolution_target,
    }


def build_coverage_report(
    store,
    *,
    engine_version: str,
    surface: dict[str, Any] | None = None,
    effect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    files = store.query(
        "SELECT id,path,coverage,content_available,acquisition_state,attributes_json FROM files ORDER BY path,id"
    )
    nodes = store.query(
        "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json FROM nodes ORDER BY kind,path,name,id"
    )
    edges = store.query(
        "SELECT id,src,dst,kind,coverage,attributes_json,evidence_ids_json FROM edges ORDER BY kind,src,dst,id"
    )
    findings = store.query(
        "SELECT id,kind,title,status,attributes_json,evidence_ids_json FROM findings ORDER BY kind,title,id"
    )
    semantic_objects = store.query(
        "SELECT id,object_type,subtype,label,coverage,attributes_json FROM semantic_objects ORDER BY object_type,subtype,label,id"
    )
    semantic_relations = store.query(
        "SELECT id,src,dst,kind,status,attributes_json,evidence_ids_json FROM semantic_relations ORDER BY kind,src,dst,id"
    )
    completeness = list(store.completeness_dimensions())
    surface = surface or surface_closure(store)
    effect = effect or effect_closure(store)
    gaps: list[dict[str, Any]] = []

    for row in files:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        attrs = _attrs(row)
        if not bool(row.get("content_available")):
            gaps.append(_gap(
                "acquisition", str(row["id"]), state, "CONTENT_UNAVAILABLE", str(row["path"]),
                "obtain verified specimen bytes for this accounted path",
                path=str(row["path"]), object_kind="file",
                detail=str(row.get("acquisition_state") or "content unavailable"),
            ))
        elif state in UNRESOLVED_STATES:
            reason = "PARSER_BUDGET_STOPPED" if attrs.get("parser_state") == "BUDGET_STOPPED" else "FILE_" + state
            gaps.append(_gap(
                "file-coverage", str(row["id"]), state, reason, str(row["path"]),
                "increase deterministic parser or adapter coverage for this file",
                path=str(row["path"]), object_kind="file",
                detail=str(attrs.get("scan_budget_reason") or attrs.get("parser_state") or state),
            ))

    for row in nodes:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        if state in UNRESOLVED_STATES:
            gaps.append(_gap(
                "node-coverage", str(row["id"]), state, "NODE_" + state,
                str(row.get("name") or row["id"]),
                "establish stronger mechanical evidence for this anatomical object",
                path=row.get("path"), object_kind=str(row.get("kind") or "node"),
                evidence_ids=_evidence_ids(row),
            ))

    for row in edges:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        if state in UNRESOLVED_STATES:
            gaps.append(_gap(
                "edge-coverage", str(row["id"]), state, "EDGE_" + state,
                f"{row.get('src')} --{row.get('kind')}--> {row.get('dst')}",
                "establish stronger mechanical evidence for this graph relation",
                object_kind=str(row.get("kind") or "edge"), evidence_ids=_evidence_ids(row),
            ))

    for row in findings:
        state = str(row.get("status") or "UNKNOWN").upper()
        if state in UNRESOLVED_STATES:
            attrs = _attrs(row)
            gaps.append(_gap(
                "finding", str(row["id"]), state,
                "FINDING_" + str(row.get("kind") or "UNKNOWN").upper(),
                str(row.get("title") or row["id"]),
                "resolve or further bound this scanner finding without promoting unsupported claims",
                object_kind=str(row.get("kind") or "finding"), evidence_ids=_evidence_ids(row),
                detail=str(attrs.get("meaning") or attrs.get("detail") or attrs.get("error") or state),
            ))

    for row in completeness:
        state = str(row.get("state") or "UNKNOWN").upper()
        if state not in NON_GAP_COMPLETENESS:
            gaps.append(_gap(
                "completeness", str(row["id"]), state, "COMPLETENESS_" + state,
                str(row.get("label") or row.get("key") or row["id"]),
                "resolve remaining evidence dependencies for this completeness dimension",
                object_kind="completeness_dimension", evidence_ids=_evidence_ids(row),
                detail=str(row.get("key") or ""),
            ))

    for row in surface.get("records") or []:
        state = str(row.get("closure") or "UNKNOWN").upper()
        if state in {"PARTIAL", "UNRESOLVED"}:
            gaps.append(_gap(
                "surface-closure", str(row["surface_id"]), state, "SURFACE_" + state,
                str(row.get("name") or row["surface_id"]),
                "resolve the route from this human surface to a handler or input consumer",
                path=row.get("path"), object_kind=str(row.get("surface_type") or "human_surface"),
                detail=f"route_edge_count={row.get('route_edge_count', 0)}",
            ))

    for row in effect.get("records") or []:
        state = str(row.get("effect_closure") or "UNKNOWN").upper()
        if state in {"PARTIAL", "UNRESOLVED"}:
            gaps.append(_gap(
                "effect-closure", str(row["surface_id"]), state, "EFFECT_" + state,
                str(row.get("name") or row["surface_id"]),
                "resolve the route to a supported state, effect, boundary, or feedback terminal",
                object_kind=str(row.get("surface_type") or "human_surface"),
                detail=f"terminal_count={row.get('terminal_count', 0)}; feedback_count={row.get('feedback_count', 0)}",
            ))

    gaps.sort(key=lambda x: (
        x["category"], x["state"], str(x.get("path") or ""), x["label"], x["object_id"], x["gap_id"]
    ))
    by_category = Counter(row["category"] for row in gaps)
    by_state = Counter(row["state"] for row in gaps)

    return {
        "schema_version": COVERAGE_REPORT_SCHEMA,
        "engine_version": engine_version,
        "authority": {
            "canonical_store": "scan_index.sqlite",
            "projection_only": True,
            "may_modify_canonical_state": False,
            "scalar_confidence_score": False,
        },
        "coverage": {
            "files": {"total": len(files), "states": _state_counts(files, "coverage")},
            "nodes": {
                "total": len(nodes), "states": _state_counts(nodes, "coverage"),
                "by_kind": _grouped_state_counts(nodes, "kind", "coverage"),
            },
            "edges": {
                "total": len(edges), "states": _state_counts(edges, "coverage"),
                "by_kind": _grouped_state_counts(edges, "kind", "coverage"),
            },
            "findings": {
                "total": len(findings), "states": _state_counts(findings, "status"),
                "by_kind": _grouped_state_counts(findings, "kind", "status"),
            },
            "semantic_objects": {
                "total": len(semantic_objects), "states": _state_counts(semantic_objects, "coverage"),
                "by_type": _grouped_state_counts(semantic_objects, "object_type", "coverage"),
            },
            "semantic_relations": {
                "total": len(semantic_relations), "states": _state_counts(semantic_relations, "status"),
                "by_kind": _grouped_state_counts(semantic_relations, "kind", "status"),
            },
            "completeness_dimensions": {
                "total": len(completeness), "states": _state_counts(completeness, "state"),
            },
        },
        "closure": {
            "surface": {
                key: surface.get(key)
                for key in ("state", "surface_count", "presented_surface_count", "bound_count", "partial_count", "unresolved_count", "closure_ratio")
            },
            "effect": {
                key: effect.get(key)
                for key in ("state", "surface_count", "closed_count", "partial_count", "unresolved_count", "feedback_observed_count", "closure_ratio")
            },
        },
        "gaps": {
            "schema_version": GAPS_SCHEMA,
            "gap_count": len(gaps),
            "by_category": dict(sorted(by_category.items())),
            "by_state": dict(sorted(by_state.items())),
            "records": gaps,
        },
    }


def render_coverage_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# SCAN Coverage Report", "",
        f"Schema: {report['schema_version']}",
        f"Engine: {report['engine_version']}", "",
        "This is a deterministic projection of scan_index.sqlite. It does not assign a scalar confidence score and cannot promote canonical evidence.",
        "", "## Coverage states", "",
        "| Domain | Total | States |", "|---|---:|---|",
    ]
    for key in ("files", "nodes", "edges", "findings", "semantic_objects", "semantic_relations", "completeness_dimensions"):
        row = report["coverage"][key]
        lines.append(f"| {key.replace('_', ' ')} | {row['total']} | {json.dumps(row['states'], sort_keys=True)} |")
    surface = report["closure"]["surface"]
    effect = report["closure"]["effect"]
    gaps = report["gaps"]
    lines += [
        "", "## Human-surface closure", "",
        f"- State: {surface.get('state') or 'UNKNOWN'}",
        f"- Actionable surfaces: {surface.get('surface_count') or 0}",
        f"- Bound: {surface.get('bound_count') or 0}",
        f"- Partial: {surface.get('partial_count') or 0}",
        f"- Unresolved: {surface.get('unresolved_count') or 0}",
        f"- Presented surfaces outside action denominator: {surface.get('presented_surface_count') or 0}",
        "", "## Effect closure", "",
        f"- State: {effect.get('state') or 'UNKNOWN'}",
        f"- Surfaces evaluated: {effect.get('surface_count') or 0}",
        f"- Closed: {effect.get('closed_count') or 0}",
        f"- Partial: {effect.get('partial_count') or 0}",
        f"- Unresolved: {effect.get('unresolved_count') or 0}",
        f"- Feedback observed: {effect.get('feedback_observed_count') or 0}",
        "", "## Unresolved gap summary", "",
        f"- Gap records: {gaps['gap_count']}",
        f"- By state: {json.dumps(gaps['by_state'], sort_keys=True)}",
        f"- By category: {json.dumps(gaps['by_category'], sort_keys=True)}",
        "", "See gaps.md and gaps.json for canonical IDs, evidence IDs, and resolution targets.", "",
    ]
    return "\n".join(lines)


def render_gaps_markdown(report: dict[str, Any]) -> str:
    gaps = report["gaps"]
    lines = [
        "# SCAN Unresolved Gaps", "",
        f"Schema: {gaps['schema_version']}",
        f"Gap records: {gaps['gap_count']}", "",
        "This checklist is derived from canonical coverage and closure state. It is not a priority ranking and does not change evidence.",
        "",
    ]
    if not gaps["records"]:
        return "\n".join(lines + ["No unresolved gaps were projected.", ""])

    lines += [
        "| Category | State | Object | Kind | Path | Reason | Evidence | Resolution target |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def cell(value: Any) -> str:
        value = " ".join(str(value or "").split()).replace("|", "\\|")
        return value if len(value) <= 160 else value[:159] + "…"

    for row in gaps["records"]:
        lines.append(
            f"| {cell(row['category'])} | {cell(row['state'])} | {cell(row['object_id'])} {cell(row['label'])} | "
            f"{cell(row.get('object_kind'))} | {cell(row.get('path'))} | {cell(row['reason_code'])} | "
            f"{cell(', '.join(row.get('evidence_ids') or []))} | {cell(row['resolution_target'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def write_coverage_outputs(
    store,
    output: Path,
    *,
    engine_version: str,
    surface: dict[str, Any] | None = None,
    effect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_coverage_report(store, engine_version=engine_version, surface=surface, effect=effect)
    files = {
        "coverage_report.json": json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "coverage_report.md": render_coverage_markdown(report),
        "gaps.json": json.dumps(report["gaps"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "gaps.md": render_gaps_markdown(report),
    }
    for name, content in files.items():
        (output / name).write_text(content, encoding="utf-8")
    return {
        "schema_version": COVERAGE_REPORT_SCHEMA,
        "state": "PASS",
        "gap_count": report["gaps"]["gap_count"],
        "files": sorted(files),
    }
