from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from scan import __version__
from scan.engine import ScanEngine
from scan.store import Store
from scan.triage_ranking import build_triage_ranking, write_triage_outputs


FIXTURE = Path(__file__).parent / "fixtures" / "qualification_sample"


def _scan(tmp_path: Path) -> Path:
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "triage-ranking-fixture")
    return out


def test_ordinary_scan_emits_triage_projection(tmp_path: Path):
    out = _scan(tmp_path)
    for name in ("triage_ranking.json", "triage_ranking.md"):
        assert (out / name).is_file(), name

    report = json.loads((out / "triage_ranking.json").read_text(encoding="utf-8"))
    gaps = json.loads((out / "gaps.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "scan-triage-ranking/0.1"
    assert report["engine_version"] == __version__ == "0.36.0"
    assert report["ranked_count"] == gaps["gap_count"]
    assert report["authority"] == {
        "canonical_store": "scan_index.sqlite",
        "projection_only": True,
        "importance_not_truth": True,
        "confidence_effect": "NONE",
        "promotion_effect": "NONE",
        "canonical_write_allowed": False,
        "llm_required": False,
    }
    assert report["ranking_policy"]["state_used_as_weight"] is False
    assert report["ranking_policy"]["category_used_as_weight"] is False


def test_scores_are_transparent_bounded_and_sorted(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "triage_ranking.json").read_text(encoding="utf-8"))
    previous = None
    for index, row in enumerate(report["rankings"], start=1):
        assert row["rank"] == index
        assert row["investigation_score"] == sum(row["components"].values())
        assert 0 <= row["investigation_score"] <= 100
        assert row["importance_only"] is True
        assert row["confidence_effect"] == "NONE"
        assert row["promotion_effect"] == "NONE"
        assert row["canonical_write_allowed"] is False
        if previous is not None:
            assert previous >= row["investigation_score"]
        previous = row["investigation_score"]


def test_regeneration_is_deterministic_and_db_remains_readonly(tmp_path: Path):
    out = _scan(tmp_path)
    db = out / "scan_index.sqlite"
    before = sha256(db.read_bytes()).hexdigest()

    coverage = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    challenges = json.loads((out / "uncertainty_challenges.json").read_text(encoding="utf-8"))
    first = tmp_path / "first"
    second = tmp_path / "second"

    for target in (first, second):
        store = Store(db, readonly=True)
        try:
            write_triage_outputs(
                store,
                target,
                engine_version=__version__,
                coverage_report=coverage,
                challenge_report=challenges,
            )
        finally:
            store.close()

    after = sha256(db.read_bytes()).hexdigest()
    assert before == after
    assert (first / "triage_ranking.json").read_bytes() == (second / "triage_ranking.json").read_bytes()
    assert (first / "triage_ranking.md").read_bytes() == (second / "triage_ranking.md").read_bytes()


class FakeStore:
    def __init__(self, rows: dict[str, list[dict]]):
        self.rows = rows

    def query(self, sql, args=()):
        for table in (
            "nodes", "edges", "semantic_objects", "semantic_relations",
        ):
            if f"FROM {table}" in sql:
                return [dict(row) for row in self.rows.get(table, [])]
        return []


def _coverage(gaps: list[dict]) -> dict:
    return {
        "schema_version": "scan-coverage-report/0.1",
        "gaps": {
            "schema_version": "scan-gaps/0.1",
            "gap_count": len(gaps),
            "records": gaps,
        },
    }


def _challenges(rows: list[dict]) -> dict:
    return {
        "schema_version": "scan-uncertainty-challenges/0.1",
        "challenge_count": len(rows),
        "challenges": rows,
    }


def test_graph_impact_outranks_isolated_gap_without_using_state_weight():
    gaps = [
        {
            "gap_id": "gap-central", "category": "node-coverage", "object_id": "node:central",
            "state": "PARTIAL", "label": "central", "path": "central.cpp",
        },
        {
            "gap_id": "gap-isolated", "category": "node-coverage", "object_id": "node:isolated",
            "state": "BLOCKED", "label": "isolated", "path": "isolated.cpp",
        },
    ]
    challenges = [
        {
            "gap_id": "gap-central", "challenge_kind": "RECHECK_LOCAL_GRAPH",
            "disposition": "MECHANICAL_RECHECK_AVAILABLE",
        },
        {
            "gap_id": "gap-isolated", "challenge_kind": "RECHECK_LOCAL_GRAPH",
            "disposition": "NO_LOCAL_SUPPORT_FOUND",
        },
    ]
    rows = {
        "nodes": [
            {
                "id": "surface:1", "file_id": "file:surface", "kind": "human_surface",
                "name": "Save", "path": "ui.cpp", "coverage": "MAPPED",
                "attributes_json": '{"surface_role":"input"}',
            },
            {
                "id": "node:central", "file_id": "file:central", "kind": "handler_reference",
                "name": "save", "path": "central.cpp", "coverage": "PARTIAL",
                "attributes_json": "{}",
            },
            {
                "id": "effect:1", "file_id": "file:central", "kind": "effect",
                "name": "filesystem_write", "path": "central.cpp", "coverage": "MAPPED",
                "attributes_json": "{}",
            },
            {
                "id": "node:isolated", "file_id": "file:isolated", "kind": "symbol",
                "name": "isolated", "path": "isolated.cpp", "coverage": "BLOCKED",
                "attributes_json": "{}",
            },
        ],
        "edges": [
            {
                "id": "edge:surface-central", "src": "surface:1", "dst": "node:central",
                "kind": "routes_to", "coverage": "MAPPED",
            },
            {
                "id": "edge:central-effect", "src": "node:central", "dst": "effect:1",
                "kind": "produces_effect", "coverage": "MAPPED",
            },
        ],
        "semantic_objects": [
            {
                "id": "node:central", "object_type": "ANATOMICAL_OBJECT", "subtype": "handler_reference",
                "label": "save", "coverage": "PARTIAL",
            },
            {
                "id": "anchor:save", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior",
                "label": "save behavior", "coverage": "MAPPED",
            },
            {
                "id": "node:isolated", "object_type": "ANATOMICAL_OBJECT", "subtype": "symbol",
                "label": "isolated", "coverage": "BLOCKED",
            },
        ],
        "semantic_relations": [
            {
                "id": "rel:anchor", "src": "node:central", "dst": "anchor:save",
                "kind": "supports_anchor", "status": "MAPPED",
            }
        ],
    }
    report = build_triage_ranking(
        FakeStore(rows),
        engine_version="0.36.0",
        coverage_report=_coverage(gaps),
        challenge_report=_challenges(challenges),
    )
    first, second = report["rankings"]
    assert first["gap_id"] == "gap-central"
    assert first["investigation_score"] > second["investigation_score"]
    assert first["raw_signals"]["reachable_actionable_surface_count"] == 1
    assert first["raw_signals"]["reachable_terminal_count"] == 1
    assert first["raw_signals"]["reconstruction_anchor_count"] == 1
    assert first["components"]["mechanical_recheck_support"] == 10
    assert second["source_state"] == "BLOCKED"
    assert second["investigation_score"] == 0
    assert report["ranking_policy"]["state_used_as_weight"] is False


def test_connectivity_is_capped_so_hubs_cannot_dominate_every_other_signal():
    gaps = [{
        "gap_id": "gap-hub", "category": "node-coverage", "object_id": "node:hub",
        "state": "PARTIAL", "label": "hub", "path": "hub.cpp",
    }]
    nodes = [{
        "id": "node:hub", "file_id": "file:hub", "kind": "symbol",
        "name": "logger", "path": "hub.cpp", "coverage": "PARTIAL", "attributes_json": "{}",
    }]
    edges = []
    for index in range(50):
        node_id = f"node:{index}"
        nodes.append({
            "id": node_id, "file_id": f"file:{index}", "kind": "symbol",
            "name": node_id, "path": f"{index}.cpp", "coverage": "MAPPED", "attributes_json": "{}",
        })
        edges.append({
            "id": f"edge:{index}", "src": "node:hub", "dst": node_id,
            "kind": "references", "coverage": "MAPPED",
        })
    report = build_triage_ranking(
        FakeStore({
            "nodes": nodes,
            "edges": edges,
            "semantic_objects": [],
            "semantic_relations": [],
        }),
        engine_version="0.36.0",
        coverage_report=_coverage(gaps),
        challenge_report=_challenges([{
            "gap_id": "gap-hub", "challenge_kind": "RECHECK_LOCAL_GRAPH",
            "disposition": "NO_LOCAL_SUPPORT_FOUND",
        }]),
    )
    row = report["rankings"][0]
    assert row["raw_signals"]["incident_edge_degree"] == 50
    assert row["components"]["structural_connectivity"] == 20
    assert row["investigation_score"] == 20
