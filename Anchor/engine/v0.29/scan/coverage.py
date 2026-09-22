from __future__ import annotations

"""Deterministic coverage and unresolved-gap projections.

This module is downstream of the canonical SQLite store. It does not assign,
upgrade, downgrade, or otherwise mutate SCAN evidence states.
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from .integrity import effect_closure, surface_closure


COVERAGE_REPORT_SCHEMA = "scan-coverage-report/0.1"
GAP_STATES = {"PARTIAL", "BLOCKED", "UNKNOWN"}
COVERAGE_ORDER = ("MAPPED", "PARTIAL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE")


def _json(value: str | None, default):
    if value in (None, ""):
        return default
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def _counts(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts = Counter(str(row.get(field) or "UNKNOWN").upper() for row in rows)
    ordered: dict[str, int] = {}
    for state in COVERAGE_ORDER:
        if state in counts:
            ordered[state] = counts[state]
    for state in sorted(set(counts) - set(COVERAGE_ORDER)):
        ordered[state] = counts[state]
    return ordered


def _gap(
    *,
    category: str,
    source_kind: str,
    source_id: str,
    state: str,
    label: str,
    path: str | None = None,
    evidence_ids: list[str] | None = None,
    reason: str,
    resolution_hint: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "category": category,
        "source_kind": source_kind,
        "source_id": source_id,
        "state": str(state or "UNKNOWN").upper(),
        "label": label,
        "path": path,
        "evidence_ids": sorted(set(evidence_ids or [])),
        "reason": reason,
        "resolution_hint": resolution_hint,
        "details": details or {},
    }


def _gap_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    state_rank = {"BLOCKED": "0", "UNKNOWN": "1", "PARTIAL": "2", "MAPPED": "3"}
    return (
        str(row.get("category") or ""),
        state_rank.get(str(row.get("state") or ""), "9"),
        str(row.get("path") or ""),
        str(row.get("label") or ""),
        str(row.get("source_id") or ""),
    )


def build_coverage_report(
    store,
    *,
    surface: dict[str, Any] | None = None,
    effect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a read-only coverage/gap view over the canonical store."""

    surface = surface or surface_closure(store)
    effect = effect or effect_closure(store)

    files = store.query(
        "SELECT id,path,coverage,content_available,acquisition_state,attributes_json "
        "FROM files ORDER BY path,id"
    )
    nodes = store.query(
        "SELECT id,kind,name,path,coverage,attributes_json,evidence_ids_json "
        "FROM nodes ORDER BY kind,path,name,id"
    )
    edges = store.query(
        "SELECT id,src,dst,kind,coverage,attributes_json,evidence_ids_json "
        "FROM edges ORDER BY kind,src,dst,id"
    )
    findings = store.query(
        "SELECT id,kind,title,status,attributes_json,evidence_ids_json "
        "FROM findings ORDER BY kind,title,id"
    )
    evidence = store.query(
        "SELECT id,path,evidence_class,extractor FROM evidence ORDER BY path,id"
    )
    semantic_objects = store.semantic_objects()
    semantic_relations = store.semantic_relations()
    completeness = store.completeness_dimensions()

    node_by_id = {row["id"]: row for row in nodes}
    gaps: list[dict[str, Any]] = []

    for row in files:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        attrs = _json(row.get("attributes_json"), {})
        if state not in GAP_STATES and bool(row.get("content_available")):
            continue
        if not bool(row.get("content_available")):
            category = "acquisition"
            reason = (
                f"Verified source bytes are unavailable ({row.get('acquisition_state') or 'UNKNOWN'}); "
                "the path is accounted for but cannot be parser evidence."
            )
            hint = "Acquire and verify the source bytes for this exact specimen revision, then rescan."
        else:
            category = "parser"
            failures = attrs.get("adapter_failures") or []
            parser_state = attrs.get("parser_state")
            reason = "File-level parser coverage is not complete."
            if parser_state:
                reason += f" Parser state: {parser_state}."
            if failures:
                reason += f" Adapter failures recorded: {len(failures)}."
            hint = "Resolve the parser/adapter or resource-limit cause for this file, then rescan."
        gaps.append(_gap(
            category=category,
            source_kind="file",
            source_id=row["id"],
            state=state,
            label=str(row.get("path") or row["id"]),
            path=row.get("path"),
            reason=reason,
            resolution_hint=hint,
            details={"acquisition_state": row.get("acquisition_state")},
        ))

    for row in nodes:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        if state not in GAP_STATES:
            continue
        gaps.append(_gap(
            category="mechanical-object",
            source_kind=str(row.get("kind") or "node"),
            source_id=row["id"],
            state=state,
            label=str(row.get("name") or row["id"]),
            path=row.get("path"),
            evidence_ids=_json(row.get("evidence_ids_json"), []),
            reason="The extracted mechanical object is not fully established by current evidence.",
            resolution_hint="Acquire stronger direct/parser evidence for this object or preserve the current uncertainty.",
        ))

    for row in edges:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        if state not in GAP_STATES:
            continue
        gaps.append(_gap(
            category="mechanical-relation",
            source_kind=str(row.get("kind") or "edge"),
            source_id=row["id"],
            state=state,
            label=f"{row.get('src')} -> {row.get('dst')}",
            evidence_ids=_json(row.get("evidence_ids_json"), []),
            reason="The mechanical relationship is not fully established by current evidence.",
            resolution_hint="Establish the route/relationship with stronger evidence or preserve the current uncertainty.",
        ))

    for row in findings:
        state = str(row.get("status") or "UNKNOWN").upper()
        if state not in GAP_STATES:
            continue
        attrs = _json(row.get("attributes_json"), {})
        kind = str(row.get("kind") or "finding")
        category = {
            "acquisition_gap": "acquisition",
            "parser_failure": "parser",
            "scan_budget": "resource-limit",
            "coverage_gap": "coverage-finding",
        }.get(kind, "coverage-finding")
        gaps.append(_gap(
            category=category,
            source_kind=kind,
            source_id=row["id"],
            state=state,
            label=str(row.get("title") or row["id"]),
            evidence_ids=_json(row.get("evidence_ids_json"), []),
            reason=str(attrs.get("meaning") or "SCAN recorded an unresolved coverage finding."),
            resolution_hint="Resolve the finding's recorded cause, collect the missing evidence, and rescan.",
            details={k: attrs[k] for k in sorted(attrs) if k in {
                "reason", "error_type", "adapter", "acquisition_states",
                "parser_eligible_files_not_fully_processed",
            }},
        ))

    for row in semantic_objects:
        state = str(row.get("coverage") or "UNKNOWN").upper()
        if state not in GAP_STATES:
            continue
        attrs = row.get("attributes") or {}
        gaps.append(_gap(
            category="semantic-object",
            source_kind=str(row.get("object_type") or "semantic_object"),
            source_id=row["id"],
            state=state,
            label=str(row.get("label") or row["id"]),
            path=attrs.get("path"),
            reason="The semantic/evidence-graph object retains unresolved coverage.",
            resolution_hint="Trace the object with SCAN why/impact and acquire stronger upstream evidence before promotion.",
        ))

    for row in semantic_relations:
        state = str(row.get("status") or "UNKNOWN").upper()
        if state not in GAP_STATES:
            continue
        gaps.append(_gap(
            category="semantic-relation",
            source_kind=str(row.get("kind") or "semantic_relation"),
            source_id=row["id"],
            state=state,
            label=f"{row.get('src')} -> {row.get('dst')}",
            evidence_ids=row.get("evidence_ids") or [],
            reason="The semantic/evidence-graph relation retains unresolved support.",
            resolution_hint="Trace both endpoints and strengthen the relation's proof path; do not promote it without evidence.",
        ))

    for row in completeness:
        state = str(row.get("state") or "UNKNOWN").upper()
        if state not in GAP_STATES:
            continue
        gaps.append(_gap(
            category="completeness-dimension",
            source_kind="coverage_dimension",
            source_id=row["id"],
            state=state,
            label=str(row.get("label") or row.get("key") or row["id"]),
            evidence_ids=row.get("evidence_ids") or [],
            reason=f"Completeness dimension {row.get('key')} remains {state}.",
            resolution_hint="Resolve the underlying child/evidence gaps represented by this dimension; the dimension itself is not an authority.",
            details={"key": row.get("key"), "parent_id": row.get("parent_id")},
        ))

    for row in surface.get("records") or []:
        closure = str(row.get("closure") or "UNRESOLVED").upper()
        if closure == "BOUND":
            continue
        source = node_by_id.get(row.get("surface_id")) or {}
        state = "PARTIAL" if closure == "PARTIAL" else "UNKNOWN"
        gaps.append(_gap(
            category="surface-binding",
            source_kind="human_surface",
            source_id=str(row.get("surface_id")),
            state=state,
            label=str(row.get("name") or row.get("surface_id")),
            path=row.get("path"),
            evidence_ids=_json(source.get("evidence_ids_json"), []),
            reason=f"Human input surface binding closure is {closure}.",
            resolution_hint="Establish a mechanically supported route from the surface to a handler/input consumer, or preserve it as unresolved.",
            details={
                "surface_type": row.get("surface_type"),
                "route_edge_count": row.get("route_edge_count"),
            },
        ))

    for row in effect.get("records") or []:
        closure = str(row.get("effect_closure") or "UNRESOLVED").upper()
        if closure == "CLOSED":
            continue
        source = node_by_id.get(row.get("surface_id")) or {}
        state = "PARTIAL" if closure == "PARTIAL" else "UNKNOWN"
        gaps.append(_gap(
            category="effect-closure",
            source_kind="human_surface",
            source_id=str(row.get("surface_id")),
            state=state,
            label=str(row.get("name") or row.get("surface_id")),
            path=source.get("path"),
            evidence_ids=_json(source.get("evidence_ids_json"), []),
            reason=f"Surface-to-terminal effect/state/NEST/feedback closure is {closure}.",
            resolution_hint="Establish a supported terminal effect/state/boundary/feedback route, or preserve the unresolved closure.",
            details={
                "surface_type": row.get("surface_type"),
                "binding_closure": row.get("binding_closure"),
                "terminal_count": row.get("terminal_count"),
                "feedback_count": row.get("feedback_count"),
            },
        ))

    gaps.sort(key=_gap_sort_key)
    by_category: dict[str, Counter[str]] = defaultdict(Counter)
    for gap in gaps:
        by_category[gap["category"]][gap["state"]] += 1

    return {
        "schema_version": COVERAGE_REPORT_SCHEMA,
        "projection_state": "PASS",
        "authority": {
            "canonical_store": "scan_index.sqlite",
            "classification_mutation": "NONE",
            "scalar_confidence_score": "NOT_USED",
            "statement": (
                "This report is a deterministic projection of canonical SCAN evidence and closure state. "
                "It cannot promote or downgrade evidence."
            ),
        },
        "coverage": {
            "files": _counts(files, "coverage"),
            "nodes": _counts(nodes, "coverage"),
            "edges": _counts(edges, "coverage"),
            "findings": _counts(findings, "status"),
            "semantic_objects": _counts(semantic_objects, "coverage"),
            "semantic_relations": _counts(semantic_relations, "status"),
            "completeness_dimensions": _counts(completeness, "state"),
        },
        "evidence": {
            "record_count": len(evidence),
            "class_counts": dict(sorted(Counter(str(row.get("evidence_class") or "UNKNOWN") for row in evidence).items())),
            "extractor_counts": dict(sorted(Counter(str(row.get("extractor") or "UNKNOWN") for row in evidence).items())),
        },
        "acquisition": {
            "file_count": len(files),
            "content_available_count": sum(1 for row in files if bool(row.get("content_available"))),
            "content_unavailable_count": sum(1 for row in files if not bool(row.get("content_available"))),
            "state_counts": dict(sorted(Counter(str(row.get("acquisition_state") or "UNKNOWN") for row in files).items())),
        },
        "closure": {
            "surface": {k: v for k, v in surface.items() if k != "records"},
            "effect": {k: v for k, v in effect.items() if k != "records"},
        },
        "gaps": {
            "count": len(gaps),
            "state_counts": dict(sorted(Counter(gap["state"] for gap in gaps).items())),
            "category_counts": {
                category: dict(sorted(states.items()))
                for category, states in sorted(by_category.items())
            },
            "records": gaps,
        },
    }


def render_coverage_report(report: dict[str, Any]) -> str:
    lines = [
        "# SCAN Coverage Report",
        "",
        "> Derived projection only. scan_index.sqlite remains authoritative. "
        "This report does not reclassify evidence and does not use a scalar confidence score.",
        "",
        "## Coverage states",
        "",
        "| Layer | MAPPED | PARTIAL | BLOCKED | UNKNOWN | N/A |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    coverage = report.get("coverage") or {}
    for layer in (
        "files", "nodes", "edges", "findings", "semantic_objects",
        "semantic_relations", "completeness_dimensions",
    ):
        counts = coverage.get(layer) or {}
        lines.append(
            f"| {layer.replace('_', ' ')} | {counts.get('MAPPED', 0)} | {counts.get('PARTIAL', 0)} | "
            f"{counts.get('BLOCKED', 0)} | {counts.get('UNKNOWN', 0)} | {counts.get('NOT_APPLICABLE', 0)} |"
        )

    surface = ((report.get("closure") or {}).get("surface") or {})
    effect = ((report.get("closure") or {}).get("effect") or {})
    acquisition = report.get("acquisition") or {}
    gaps = report.get("gaps") or {}
    lines += [
        "",
        "## Closure",
        "",
        f"- Human surfaces: {surface.get('surface_count', 0)} total; "
        f"{surface.get('bound_count', 0)} bound, {surface.get('partial_count', 0)} partial, "
        f"{surface.get('unresolved_count', 0)} unresolved.",
        f"- Effect closure: {effect.get('surface_count', 0)} total; "
        f"{effect.get('closed_count', 0)} closed, {effect.get('partial_count', 0)} partial, "
        f"{effect.get('unresolved_count', 0)} unresolved.",
        "",
        "## Acquisition",
        "",
        f"- Files accounted for: {acquisition.get('file_count', 0)}",
        f"- Verified content available: {acquisition.get('content_available_count', 0)}",
        f"- Content unavailable: {acquisition.get('content_unavailable_count', 0)}",
        "",
        "## Unresolved queue",
        "",
        f"- Total projected gap records: {gaps.get('count', 0)}",
    ]
    for category, counts in sorted((gaps.get("category_counts") or {}).items()):
        summary = ", ".join(f"{state}={count}" for state, count in sorted(counts.items()))
        lines.append(f"- {category}: {summary}")
    lines += [
        "",
        "See gaps.md for the canonical-ID checklist. Resolve gaps by collecting stronger evidence and rescanning; "
        "never edit this projection to change canonical state.",
        "",
    ]
    return "\n".join(lines)


def render_gaps(report: dict[str, Any]) -> str:
    records = ((report.get("gaps") or {}).get("records") or [])
    lines = [
        "# SCAN Unresolved Gaps",
        "",
        "> Checklist projection only. Items disappear or change state only when upstream canonical evidence/closure changes.",
        "",
    ]
    if not records:
        lines += ["No PARTIAL, BLOCKED, or UNKNOWN gap records are projected.", ""]
        return "\n".join(lines)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        grouped[str(row.get("category") or "other")].append(row)

    for category in sorted(grouped):
        lines += [f"## {category}", ""]
        for row in grouped[category]:
            path = f" — {row['path']}" if row.get("path") else ""
            evidence = row.get("evidence_ids") or []
            evidence_text = f" — evidence: {', '.join(evidence)}" if evidence else ""
            lines.append(
                f"- {row.get('state')} {row.get('source_id')}{path} — {row.get('label')} — "
                f"{row.get('reason')} Next evidence: {row.get('resolution_hint')}{evidence_text}"
            )
        lines.append("")
    return "\n".join(lines)


def write_coverage_outputs(
    store,
    output: Path,
    *,
    surface: dict[str, Any] | None = None,
    effect: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = build_coverage_report(store, surface=surface, effect=effect)
    (output / "coverage_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (output / "coverage_report.md").write_text(render_coverage_report(report), encoding="utf-8")
    (output / "gaps.md").write_text(render_gaps(report), encoding="utf-8")
    return report
