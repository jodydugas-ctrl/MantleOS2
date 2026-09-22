from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from scan import __version__
from scan.engine import ScanEngine
from scan.store import Store
from scan.uncertainty_challenger import build_uncertainty_challenges, write_uncertainty_outputs


FIXTURE = Path(__file__).parent / "fixtures" / "qualification_sample"


def _scan(tmp_path: Path) -> Path:
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "uncertainty-challenger-fixture")
    return out


def test_ordinary_scan_emits_readonly_uncertainty_challenges(tmp_path: Path):
    out = _scan(tmp_path)
    for name in ("uncertainty_challenges.json", "uncertainty_challenges.md"):
        assert (out / name).is_file(), name

    report = json.loads((out / "uncertainty_challenges.json").read_text(encoding="utf-8"))
    gaps = json.loads((out / "gaps.json").read_text(encoding="utf-8"))

    assert report["schema_version"] == "scan-uncertainty-challenges/0.1"
    assert report["engine_version"] == __version__ == "0.35.0"
    assert report["challenge_count"] == gaps["gap_count"]
    assert report["authority"] == {
        "canonical_store": "scan_index.sqlite",
        "projection_only": True,
        "canonical_write_allowed": False,
        "promotion_allowed": False,
        "state_change_requires_mechanical_rescan_or_existing_promotion_gate": True,
        "llm_required": False,
    }


def test_every_challenge_references_existing_gap_and_only_existing_evidence(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "uncertainty_challenges.json").read_text(encoding="utf-8"))
    gaps = json.loads((out / "gaps.json").read_text(encoding="utf-8"))
    gap_ids = {row["gap_id"] for row in gaps["records"]}

    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        evidence_ids = {str(row["id"]) for row in store.query("SELECT id FROM evidence")}
    finally:
        store.close()

    for row in report["challenges"]:
        assert row["gap_id"] in gap_ids
        assert set(row["candidate_evidence_ids"]).issubset(evidence_ids)
        assert row["canonical_write_allowed"] is False
        assert row["promotion_allowed"] is False
        for forbidden in ("new_state", "promoted_state", "confidence", "score", "rank", "priority"):
            assert forbidden not in row


def test_regeneration_is_deterministic_and_does_not_mutate_canonical_db(tmp_path: Path):
    out = _scan(tmp_path)
    db = out / "scan_index.sqlite"
    before = sha256(db.read_bytes()).hexdigest()

    coverage = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    first = tmp_path / "first"
    second = tmp_path / "second"
    for target in (first, second):
        store = Store(db, readonly=True)
        try:
            write_uncertainty_outputs(
                store, target, engine_version=__version__, coverage_report=coverage,
            )
        finally:
            store.close()

    after = sha256(db.read_bytes()).hexdigest()
    assert before == after
    assert (first / "uncertainty_challenges.json").read_bytes() == (second / "uncertainty_challenges.json").read_bytes()
    assert (first / "uncertainty_challenges.md").read_bytes() == (second / "uncertainty_challenges.md").read_bytes()


class FakeStore:
    def __init__(self, rows: dict[str, list[dict]]):
        self.rows = rows

    def query(self, sql, args=()):
        for table, rows in self.rows.items():
            if f"FROM {table}" in sql:
                return [dict(row) for row in rows]
        return []


def _coverage_with_gap(gap: dict) -> dict:
    return {
        "schema_version": "scan-coverage-report/0.1",
        "gaps": {
            "schema_version": "scan-gaps/0.1",
            "gap_count": 1,
            "records": [gap],
        },
    }


def test_acquisition_gap_requires_external_input_not_reclassification():
    gap = {
        "gap_id": "gap-acquire", "category": "acquisition", "object_id": "file:1",
        "state": "BLOCKED", "reason_code": "CONTENT_UNAVAILABLE", "evidence_ids": [],
    }
    report = build_uncertainty_challenges(
        FakeStore({}), engine_version="0.35.0", coverage_report=_coverage_with_gap(gap),
    )
    row = report["challenges"][0]
    assert row["challenge_kind"] == "BLOCKED_ON_ACQUISITION"
    assert row["disposition"] == "EXTERNAL_INPUT_REQUIRED"
    assert "ACQUIRE_VERIFIED_BYTES" in row["mechanical_checks"]
    assert row["promotion_allowed"] is False


def test_partial_node_with_mapped_neighbor_surfaces_mechanical_recheck():
    gap = {
        "gap_id": "gap-node", "category": "node-coverage", "object_id": "node:partial",
        "state": "PARTIAL", "reason_code": "NODE_PARTIAL", "evidence_ids": ["ev:direct"],
    }
    rows = {
        "nodes": [
            {
                "id": "node:partial", "kind": "handler_reference", "name": "maybeSave",
                "path": "a.cpp", "coverage": "PARTIAL", "evidence_ids_json": '["ev:direct"]',
            },
            {
                "id": "node:mapped", "kind": "symbol", "name": "saveFile",
                "path": "b.cpp", "coverage": "MAPPED", "evidence_ids_json": '["ev:neighbor"]',
            },
        ],
        "edges": [
            {
                "id": "edge:1", "src": "node:partial", "dst": "node:mapped",
                "kind": "calls", "coverage": "PARTIAL", "evidence_ids_json": '["ev:edge"]',
            }
        ],
        "findings": [],
        "completeness_dimensions": [],
        "semantic_objects": [],
        "semantic_relations": [],
        "evidence": [
            {"id": "ev:direct", "file_id": "f1", "path": "a.cpp", "start_line": 1, "end_line": 1, "evidence_class": "DIRECT", "extractor": "fixture"},
            {"id": "ev:neighbor", "file_id": "f2", "path": "b.cpp", "start_line": 2, "end_line": 2, "evidence_class": "DIRECT", "extractor": "fixture"},
            {"id": "ev:edge", "file_id": "f1", "path": "a.cpp", "start_line": 3, "end_line": 3, "evidence_class": "DIRECT", "extractor": "fixture"},
        ],
    }
    report = build_uncertainty_challenges(
        FakeStore(rows), engine_version="0.35.0", coverage_report=_coverage_with_gap(gap),
    )
    row = report["challenges"][0]
    assert row["challenge_kind"] == "RECHECK_LOCAL_GRAPH"
    assert row["disposition"] == "MECHANICAL_RECHECK_AVAILABLE"
    assert row["mapped_neighbor_ids"] == ["node:mapped"]
    assert row["candidate_evidence_ids"] == ["ev:direct", "ev:edge", "ev:neighbor"]
    assert row["promotion_allowed"] is False
