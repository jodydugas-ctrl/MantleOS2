from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from scan import __version__
from scan.cli import main as canonical_main
from scan.engine import ScanEngine
from scan.layered_provenance import build_layered_provenance, write_layered_provenance_outputs
from scan.store import Store


FIXTURE = Path(__file__).parent / "fixtures" / "qualification_sample"


def _scan(tmp_path: Path) -> Path:
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "layered-provenance-fixture")
    return out


def test_ordinary_scan_emits_layered_provenance_without_duplicate_authority(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "layered_provenance.json").read_text(encoding="utf-8"))

    assert report["schema_version"] == "scan-layered-provenance/0.1"
    assert report["engine_version"] == __version__ == "0.34.0"
    assert report["authority"] == {
        "canonical_store": "scan_index.sqlite",
        "projection_only": True,
        "duplicates_canonical_graph": False,
        "canonical_write_allowed": False,
        "coverage_preserved_per_object": True,
        "higher_layer_text_does_not_upgrade_lower_layer_evidence": True,
    }
    assert report["layer_model"]["E0"]["object_count"] > 0
    assert report["layer_model"]["E1"]["object_count"] > 0
    assert report["layer_model"]["E4"]["canonical"] is False


def test_layer_counts_and_coverage_reconcile_to_canonical_semantic_graph(tmp_path: Path):
    out = _scan(tmp_path)
    report = json.loads((out / "layered_provenance.json").read_text(encoding="utf-8"))
    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        objects = store.semantic_objects()
    finally:
        store.close()

    projected = {row["object_id"]: row for row in report["objects"]}
    assert set(projected) == {row["id"] for row in objects}
    for row in objects:
        assert projected[row["id"]]["coverage"] == str(row["coverage"]).upper()


def test_regeneration_is_deterministic_and_readonly(tmp_path: Path):
    out = _scan(tmp_path)
    db = out / "scan_index.sqlite"
    before = sha256(db.read_bytes()).hexdigest()

    first = tmp_path / "first"
    second = tmp_path / "second"
    for target in (first, second):
        store = Store(db, readonly=True)
        try:
            write_layered_provenance_outputs(store, target, engine_version=__version__)
        finally:
            store.close()

    after = sha256(db.read_bytes()).hexdigest()
    assert before == after
    assert (first / "layered_provenance.json").read_bytes() == (second / "layered_provenance.json").read_bytes()
    assert (first / "layered_provenance.md").read_bytes() == (second / "layered_provenance.md").read_bytes()


class FakeStore:
    def __init__(self, objects, relations):
        self._objects = objects
        self._relations = relations

    def semantic_objects(self):
        return [dict(row) for row in self._objects]

    def semantic_relations(self):
        return [dict(row) for row in self._relations]


def test_layers_preserve_independent_epistemic_states_and_e0_lineage():
    objects = [
        {"id": "spec:1", "object_type": "SPECIMEN", "subtype": "software", "label": "spec", "coverage": "MAPPED", "attributes": {}},
        {"id": "file:1", "object_type": "FILE", "subtype": "source", "label": "a.cpp", "coverage": "MAPPED", "attributes": {}},
        {"id": "ev:1", "object_type": "EVIDENCE", "subtype": "DIRECT", "label": "direct", "coverage": "MAPPED", "attributes": {}},
        {"id": "node:1", "object_type": "ANATOMICAL_OBJECT", "subtype": "symbol", "label": "saveFile", "coverage": "MAPPED", "attributes": {}},
        {"id": "beh:1", "object_type": "BEHAVIOR", "subtype": "document-save", "label": "save behavior", "coverage": "PARTIAL", "attributes": {}},
        {"id": "anchor:1", "object_type": "RECONSTRUCTION_ANCHOR", "subtype": "behavior", "label": "save anchor", "coverage": "PARTIAL", "attributes": {}},
        {"id": "human:1", "object_type": "HUMAN_DESCRIPTION", "subtype": "summary", "label": "Save description", "coverage": "MAPPED", "attributes": {}},
    ]
    relations = [
        {"id": "r0", "src": "spec:1", "dst": "file:1", "kind": "contains", "status": "MAPPED", "attributes": {}, "evidence_ids": []},
        {"id": "r1", "src": "file:1", "dst": "ev:1", "kind": "contains_evidence", "status": "MAPPED", "attributes": {}, "evidence_ids": []},
        {"id": "r2", "src": "ev:1", "dst": "node:1", "kind": "supports", "status": "MAPPED", "attributes": {}, "evidence_ids": []},
        {"id": "r3", "src": "node:1", "dst": "beh:1", "kind": "supports", "status": "MAPPED", "attributes": {}, "evidence_ids": []},
        {"id": "r4", "src": "beh:1", "dst": "anchor:1", "kind": "supports_anchor", "status": "PARTIAL", "attributes": {}, "evidence_ids": []},
        {"id": "r5", "src": "anchor:1", "dst": "human:1", "kind": "supports", "status": "PARTIAL", "attributes": {}, "evidence_ids": []},
    ]

    report = build_layered_provenance(FakeStore(objects, relations), engine_version="0.34.0")
    by_id = {row["object_id"]: row for row in report["objects"]}

    assert by_id["ev:1"]["layer"] == "E0"
    assert by_id["node:1"]["layer"] == "E1"
    assert by_id["beh:1"]["layer"] == "E2"
    assert by_id["anchor:1"]["layer"] == "E3"
    assert by_id["human:1"]["layer"] == "E4"

    assert by_id["node:1"]["coverage"] == "MAPPED"
    assert by_id["beh:1"]["coverage"] == "PARTIAL"
    assert by_id["anchor:1"]["coverage"] == "PARTIAL"
    assert by_id["human:1"]["coverage"] == "MAPPED"
    assert by_id["human:1"]["presentation_only"] is True

    assert by_id["anchor:1"]["lineage"]["evidence_ids"] == ["ev:1"]
    assert by_id["anchor:1"]["lineage"]["source_file_ids"] == ["file:1"]
    assert by_id["anchor:1"]["lineage"]["proof_complete_to_e0"] is True
    assert by_id["human:1"]["lineage"]["evidence_ids"] == ["ev:1"]
    assert report["authority"]["higher_layer_text_does_not_upgrade_lower_layer_evidence"] is True


def test_unknown_object_types_are_visible_not_silently_assigned():
    report = build_layered_provenance(
        FakeStore(
            [{"id": "x:1", "object_type": "NEW_FUTURE_TYPE", "subtype": "x", "label": "x", "coverage": "UNKNOWN", "attributes": {}}],
            [],
        ),
        engine_version="0.34.0",
    )
    assert report["objects"][0]["layer"] == "UNCLASSIFIED"
    assert report["unclassified_object_types"] == {"NEW_FUTURE_TYPE": 1}


def test_semantic_overlay_refreshes_layered_projection(tmp_path: Path):
    out = _scan(tmp_path)
    store = Store(out / "scan_index.sqlite", readonly=True)
    try:
        source = next(row for row in store.semantic_objects() if row["object_type"] == "ANATOMICAL_OBJECT")
    finally:
        store.close()

    overlay = tmp_path / "overlay.json"
    overlay.write_text(json.dumps({
        "schema_version": "scan-semantic-overlay/0.1",
        "objects": [{
            "id": "BEH-LAYER-001",
            "object_type": "BEHAVIOR",
            "subtype": "fixture-behavior",
            "label": "Fixture derived behavior",
            "coverage": "PARTIAL",
            "attributes": {"uncertainty": "fixture"},
        }],
        "relations": [{
            "src": source["id"],
            "dst": "BEH-LAYER-001",
            "kind": "supports",
            "status": "PARTIAL",
        }],
    }), encoding="utf-8")

    rc = canonical_main([
        "ingest-knowledge",
        str(out / "scan_index.sqlite"),
        str(overlay),
        "--out-dir",
        str(out),
    ])
    assert rc == 0
    report = json.loads((out / "layered_provenance.json").read_text(encoding="utf-8"))
    behavior = next(row for row in report["objects"] if row["object_id"] == "BEH-LAYER-001")
    assert behavior["layer"] == "E2"
    assert behavior["coverage"] == "PARTIAL"
    assert behavior["lineage"]["proof_complete_to_e0"] is True

    manifest = json.loads((out / "projection_manifest.json").read_text(encoding="utf-8"))
    names = {row["name"] for row in manifest["projections"]}
    assert "layered_provenance.json" in names
    assert "layered_provenance.md" in names
