from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from scan import __version__
from scan.coverage_report import build_coverage_report, write_coverage_outputs
from scan.engine import ScanEngine
from scan.store import Store


FIXTURE = Path(__file__).parent / "fixtures" / "qualification_sample"


def _scan(tmp_path: Path) -> Path:
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "coverage-gap-fixture")
    return out


def test_ordinary_scan_emits_coverage_and_gap_projections(tmp_path: Path):
    out = _scan(tmp_path)
    for name in ("coverage_report.json", "coverage_report.md", "gaps.json", "gaps.md"):
        assert (out / name).is_file(), name

    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "scan-coverage-report/0.1"
    assert report["engine_version"] == __version__ == "0.33.0"
    assert report["authority"] == {
        "canonical_store": "scan_index.sqlite",
        "projection_only": True,
        "may_modify_canonical_state": False,
        "scalar_confidence_score": False,
    }


def test_coverage_counts_reconcile_exactly_to_canonical_store(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        expectations = {
            "files": ("files", "coverage"),
            "nodes": ("nodes", "coverage"),
            "edges": ("edges", "coverage"),
            "findings": ("findings", "status"),
            "semantic_objects": ("semantic_objects", "coverage"),
            "semantic_relations": ("semantic_relations", "status"),
            "completeness_dimensions": ("completeness_dimensions", "state"),
        }
        for key, (table, state_field) in expectations.items():
            rows = store.query(f"SELECT {state_field} FROM {table}")
            assert report["coverage"][key]["total"] == len(rows)
            direct = {}
            for row in rows:
                state = str(row.get(state_field) or "UNKNOWN").upper()
                direct[state] = direct.get(state, 0) + 1
            assert report["coverage"][key]["states"] == dict(sorted(direct.items()))
    finally:
        store.close()


def test_gap_projection_is_unranked_and_only_references_existing_objects(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    gaps = report["gaps"]["records"]
    assert all("priority" not in row and "rank" not in row and "score" not in row for row in gaps)

    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        ids = set()
        for table in ("files", "nodes", "edges", "findings", "completeness_dimensions"):
            ids.update(str(row["id"]) for row in store.query(f"SELECT id FROM {table}"))
        assert all(row["object_id"] in ids for row in gaps)
    finally:
        store.close()


def test_regeneration_from_readonly_db_is_deterministic_and_non_mutating(tmp_path: Path):
    out = _scan(tmp_path)
    db = out / "scan_index.sqlite"
    before = sha256(db.read_bytes()).hexdigest()

    first = tmp_path / "first"
    second = tmp_path / "second"
    for target in (first, second):
        store = Store(db, readonly=True)
        try:
            write_coverage_outputs(store, target, engine_version=__version__)
        finally:
            store.close()

    after = sha256(db.read_bytes()).hexdigest()
    assert before == after
    for name in ("coverage_report.json", "coverage_report.md", "gaps.json", "gaps.md"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_gap_json_is_exact_subset_of_coverage_report(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    gaps = json.loads((out / "gaps.json").read_text(encoding="utf-8"))
    assert gaps == report["gaps"]
    assert gaps["gap_count"] == len(gaps["records"])
