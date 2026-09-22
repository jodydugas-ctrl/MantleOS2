from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from scan import __version__
from scan.agent_blueprint import export_agent_blueprint
from scan.conformance_contract import parse_blueprint_manifest
from scan.engine import ScanEngine
from scan.parity_distribution import build_parity_scenarios, write_parity_distribution
from scan.store import Store


FIXTURE = Path(__file__).parent / "fixtures" / "qualification_sample"


def _scan(tmp_path: Path) -> Path:
    out = tmp_path / "scan"
    ScanEngine().scan(FIXTURE, out, "parity-distribution-fixture")
    return out


def test_blueprint_export_emits_parity_and_agents_companions(tmp_path: Path):
    scan = _scan(tmp_path)
    store = Store(scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = next(
            row["attributes"]
            for row in store.semantic_objects()
            if row["object_type"] == "SPECIMEN"
        )
        dist = tmp_path / "dist"
        blueprint = dist / "Fixture Anchor Blueprint.md"
        result = export_agent_blueprint(
            store,
            specimen,
            blueprint,
            engine_version=__version__,
        )
    finally:
        store.close()

    for name in ("parity_scenarios.json", "parity_scenarios.feature", "AGENTS.md"):
        assert (dist / name).is_file(), name

    manifest = parse_blueprint_manifest(blueprint)
    parity = json.loads((dist / "parity_scenarios.json").read_text(encoding="utf-8"))
    assert result["companions"]["scenario_count"] == manifest["summary"]["required_contract_count"]
    assert parity["scenario_count"] == manifest["summary"]["required_contract_count"]
    assert parity["authority"]["source_of_truth"] == "BLUEPRINT_EMBEDDED_CONFORMANCE_MANIFEST"
    assert parity["authority"]["independent_specification"] is False
    assert parity["authority"]["runtime_equivalence_claimed"] is False


def test_every_parity_scenario_round_trips_to_one_required_contract(tmp_path: Path):
    scan = _scan(tmp_path)
    store = Store(scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = next(
            row["attributes"]
            for row in store.semantic_objects()
            if row["object_type"] == "SPECIMEN"
        )
        blueprint = tmp_path / "Blueprint.md"
        export_agent_blueprint(store, specimen, blueprint, engine_version=__version__)
    finally:
        store.close()

    manifest = parse_blueprint_manifest(blueprint)
    parity = json.loads((tmp_path / "parity_scenarios.json").read_text(encoding="utf-8"))
    required = {row["contract_id"]: row for row in manifest["contracts"]}

    assert {row["source_contract_id"] for row in parity["scenarios"]} == set(required)
    for row in parity["scenarios"]:
        source = required[row["source_contract_id"]]
        assert row["execution_class"] == "STATIC_RESCAN"
        assert row["runtime_validation_state"] == "NOT_CLAIMED"
        assert row["coverage"] == "MAPPED"
        assert row["enforcement"] == "REQUIRED"
        assert row["contract"]["identity"] == source["identity"]
        assert row["contract"]["expected"] == source["expected"]
        assert row["contract"]["count"] == int(source.get("count") or 1)


def test_generator_does_not_promote_advisory_or_partial_contracts():
    manifest = {
        "schema_version": "scan-anchor-conformance-contract/0.1",
        "blueprint_schema": "scan-anchor-blueprint-md/0.4",
        "app_name": "fixture",
        "contracts": [
            {
                "contract_id": "REQ",
                "area": "events",
                "kind": "event",
                "coverage": "MAPPED",
                "enforcement": "REQUIRED",
                "comparison": "EXACT",
                "identity": {"name": "save"},
                "expected": {},
            },
            {
                "contract_id": "ADV",
                "area": "events",
                "kind": "handler_reference",
                "coverage": "MAPPED",
                "enforcement": "ADVISORY",
                "comparison": "COMPATIBLE",
                "identity": {"name": "maybeSave"},
                "expected": {},
            },
            {
                "contract_id": "PART",
                "area": "effects-boundaries",
                "kind": "effect",
                "coverage": "PARTIAL",
                "enforcement": "REQUIRED",
                "comparison": "EXACT",
                "identity": {"name": "maybeWrite"},
                "expected": {},
            },
        ],
    }
    report = build_parity_scenarios(
        manifest,
        blueprint_file="Blueprint.md",
        blueprint_sha256="a" * 64,
        engine_version="0.34.0",
    )
    assert report["scenario_count"] == 1
    assert report["scenarios"][0]["source_contract_id"] == "REQ"


def test_portable_regeneration_requires_only_blueprint_and_is_deterministic(tmp_path: Path):
    scan = _scan(tmp_path)
    store = Store(scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = next(
            row["attributes"]
            for row in store.semantic_objects()
            if row["object_type"] == "SPECIMEN"
        )
        blueprint = tmp_path / "Blueprint.md"
        export_agent_blueprint(store, specimen, blueprint, engine_version=__version__)
    finally:
        store.close()

    before = sha256(blueprint.read_bytes()).hexdigest()
    first = tmp_path / "first"
    second = tmp_path / "second"
    write_parity_distribution(blueprint, first, engine_version=__version__)
    write_parity_distribution(blueprint, second, engine_version=__version__)
    after = sha256(blueprint.read_bytes()).hexdigest()

    assert before == after
    for name in ("parity_scenarios.json", "parity_scenarios.feature", "AGENTS.md"):
        assert (first / name).read_bytes() == (second / name).read_bytes(), name


def test_agents_md_is_small_pointer_not_duplicate_specification(tmp_path: Path):
    scan = _scan(tmp_path)
    store = Store(scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = next(
            row["attributes"]
            for row in store.semantic_objects()
            if row["object_type"] == "SPECIMEN"
        )
        blueprint = tmp_path / "Blueprint.md"
        export_agent_blueprint(store, specimen, blueprint, engine_version=__version__)
    finally:
        store.close()

    agents = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    parity = json.loads((tmp_path / "parity_scenarios.json").read_text(encoding="utf-8"))

    assert len(agents.encode("utf-8")) < 4096
    assert blueprint.name in agents
    assert sha256(blueprint.read_bytes()).hexdigest() in agents
    assert "derived projections" in agents
    assert "does not establish runtime" in agents
    assert "candidate self-report" in agents.lower()
    for row in parity["scenarios"][:5]:
        assert row["source_contract_id"] not in agents


def test_feature_file_has_one_static_scenario_per_json_scenario(tmp_path: Path):
    scan = _scan(tmp_path)
    store = Store(scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = next(
            row["attributes"]
            for row in store.semantic_objects()
            if row["object_type"] == "SPECIMEN"
        )
        blueprint = tmp_path / "Blueprint.md"
        export_agent_blueprint(store, specimen, blueprint, engine_version=__version__)
    finally:
        store.close()

    parity = json.loads((tmp_path / "parity_scenarios.json").read_text(encoding="utf-8"))
    feature = (tmp_path / "parity_scenarios.feature").read_text(encoding="utf-8")
    assert feature.count("  Scenario: ") == parity["scenario_count"]
    assert "@static" in feature
    assert "runtime/visual/timing equivalence is not claimed" in feature


def test_existing_project_agents_file_is_preserved(tmp_path: Path):
    scan = _scan(tmp_path)
    store = Store(scan / "scan_index.sqlite", readonly=True)
    try:
        specimen = next(
            row["attributes"]
            for row in store.semantic_objects()
            if row["object_type"] == "SPECIMEN"
        )
        dist = tmp_path / "dist"
        dist.mkdir()
        existing = dist / "AGENTS.md"
        original = "# Project agent rules\n\nDo not overwrite me.\n"
        existing.write_text(original, encoding="utf-8")
        blueprint = dist / "Blueprint.md"
        result = export_agent_blueprint(store, specimen, blueprint, engine_version=__version__)
    finally:
        store.close()

    assert existing.read_text(encoding="utf-8") == original
    assert result["companions"]["agents"]["state"] == "PRESERVED_EXISTING"
    assert result["companions"]["agents"]["existing_project_instructions_preserved"] is True
    assert result["companions"]["files"]["agents"] is None
