from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path

from scan.cli import main as canonical_main
from scan.coverage import GAP_STATES, build_coverage_report, write_coverage_outputs
from scan.engine import ScanEngine
from scan.store import Store


FIXTURE = Path(__file__).parent / "fixtures" / "qualification_sample"


def _digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _counter(rows, field):
    return Counter(str(row.get(field) or "UNKNOWN").upper() for row in rows)


def test_scan_emits_coverage_and_gap_projections(tmp_path: Path):
    out = tmp_path / "scan"
    summary = ScanEngine().scan(FIXTURE, out, "v029-coverage-fixture")

    for name in ("coverage_report.json", "coverage_report.md", "gaps.md"):
        assert (out / name).is_file(), name
        assert (out / name).stat().st_size > 0

    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    assert report["schema_version"] == "scan-coverage-report/0.1"
    assert report["projection_state"] == "PASS"
    assert report["authority"]["canonical_store"] == "scan_index.sqlite"
    assert report["authority"]["classification_mutation"] == "NONE"
    assert report["authority"]["scalar_confidence_score"] == "NOT_USED"
    assert summary["coverage_report"]["gap_count"] == report["gaps"]["count"]

    manifest = json.loads((out / "projection_manifest.json").read_text(encoding="utf-8"))
    projected = {row["name"] for row in manifest["projections"]}
    assert {"coverage_report.json", "coverage_report.md", "gaps.md"} <= projected


def test_coverage_counts_reconcile_exactly_with_canonical_store(tmp_path: Path):
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "v029-reconcile")
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))

    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        sources = {
            "files": (store.query("SELECT coverage FROM files"), "coverage"),
            "nodes": (store.query("SELECT coverage FROM nodes"), "coverage"),
            "edges": (store.query("SELECT coverage FROM edges"), "coverage"),
            "findings": (store.query("SELECT status FROM findings"), "status"),
            "semantic_objects": (store.semantic_objects(), "coverage"),
            "semantic_relations": (store.semantic_relations(), "status"),
            "completeness_dimensions": (store.completeness_dimensions(), "state"),
        }
    finally:
        store.close()

    for layer, (rows, field) in sources.items():
        expected = _counter(rows, field)
        actual = Counter(report["coverage"][layer])
        assert actual == expected, (layer, actual, expected)


def test_gap_records_only_surface_existing_uncertainty(tmp_path: Path):
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "v029-gap-purity")
    report = json.loads((out / "coverage_report.json").read_text(encoding="utf-8"))
    records = report["gaps"]["records"]

    assert report["gaps"]["count"] == len(records)
    assert all(row["state"] in GAP_STATES for row in records)
    assert all(row["source_id"] for row in records)
    assert all(row["reason"] and row["resolution_hint"] for row in records)

    state_counts = Counter(row["state"] for row in records)
    assert dict(sorted(state_counts.items())) == report["gaps"]["state_counts"]

    category_counts = {}
    for row in records:
        category_counts.setdefault(row["category"], Counter())[row["state"]] += 1
    expected_categories = {
        category: dict(sorted(counts.items()))
        for category, counts in sorted(category_counts.items())
    }
    assert expected_categories == report["gaps"]["category_counts"]


def test_projection_is_read_only_and_byte_deterministic(tmp_path: Path):
    scan_out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, scan_out, "v029-readonly")
    db = scan_out / "scan_index.sqlite"
    before = _digest(db)

    first = tmp_path / "projection-a"
    second = tmp_path / "projection-b"
    store = Store(db, readonly=True)
    try:
        write_coverage_outputs(store, first)
        write_coverage_outputs(store, second)
    finally:
        store.close()

    assert _digest(db) == before
    for name in ("coverage_report.json", "coverage_report.md", "gaps.md"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_explicit_coverage_report_command_regenerates_projection(tmp_path: Path):
    scan_out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, scan_out, "v029-cli")
    regen = tmp_path / "regen"

    rc = canonical_main([
        "coverage-report",
        str(scan_out / "scan_index.sqlite"),
        "--out-dir",
        str(regen),
    ])
    assert rc == 0

    for name in ("coverage_report.json", "coverage_report.md", "gaps.md"):
        assert (regen / name).read_bytes() == (scan_out / name).read_bytes(), name


def test_builder_does_not_create_a_scalar_confidence_measure(tmp_path: Path):
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "v029-no-scalar")
    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        report = build_coverage_report(store)
    finally:
        store.close()

    payload = json.dumps(report, sort_keys=True)
    assert "confidence_score" not in payload
    assert report["authority"]["scalar_confidence_score"] == "NOT_USED"
