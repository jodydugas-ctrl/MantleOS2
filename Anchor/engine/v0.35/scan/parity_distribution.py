from __future__ import annotations

"""Portable parity-scenario and agent-discovery projections for Anchor Blueprints.

The embedded Blueprint conformance manifest remains the source of truth.
Scenarios and AGENTS.md are derived distribution aids only.
"""

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any

from .conformance_contract import parse_blueprint_manifest

PARITY_SCHEMA = "scan-parity-scenarios/0.1"
AGENTS_MARKER = "<!-- SCAN_GENERATED_AGENT_POINTER -->"


def _hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _slug(value: Any) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "")).strip("_").lower()
    return text or "unknown"


def _scenario_id(contract_id: str) -> str:
    return "PS-" + sha256(contract_id.encode("utf-8", "surrogatepass")).hexdigest()[:16]


def build_parity_scenarios(
    manifest: dict[str, Any],
    *,
    blueprint_file: str,
    blueprint_sha256: str,
    engine_version: str,
) -> dict[str, Any]:
    contracts = [
        contract for contract in (manifest.get("contracts") or [])
        if str(contract.get("enforcement") or "REQUIRED").upper() == "REQUIRED"
        and str(contract.get("coverage") or "UNKNOWN").upper() == "MAPPED"
    ]
    scenarios: list[dict[str, Any]] = []
    for contract in contracts:
        contract_id = str(contract.get("contract_id") or "")
        scenarios.append({
            "scenario_id": _scenario_id(contract_id),
            "source_contract_id": contract_id,
            "source_contract_schema": manifest.get("schema_version"),
            "area": contract.get("area"),
            "kind": contract.get("kind"),
            "coverage": str(contract.get("coverage") or "UNKNOWN").upper(),
            "enforcement": str(contract.get("enforcement") or "REQUIRED").upper(),
            "comparison": str(contract.get("comparison") or "EXACT").upper(),
            "execution_class": "STATIC_RESCAN",
            "runtime_validation_state": "NOT_CLAIMED",
            "given": {
                "text": "a reconstruction candidate based on the authoritative Anchor Blueprint",
                "blueprint_file": blueprint_file,
                "blueprint_sha256": blueprint_sha256,
            },
            "when": {
                "text": "SCAN performs a fresh read-only candidate scan and conformance comparison",
                "mechanism": "scan-body conform",
            },
            "then": {
                "text": "the source conformance contract is reported SATISFIED",
                "required_status": "SATISFIED",
            },
            "contract": {
                "identity": contract.get("identity") or {},
                "expected": contract.get("expected") or {},
                "count": int(contract.get("count") or 1),
                "source_refs": contract.get("source_refs") or [],
            },
            "tags": [
                "scan",
                "static",
                "area_" + _slug(contract.get("area")),
                "kind_" + _slug(contract.get("kind")),
            ],
        })

    scenarios.sort(key=lambda row: (str(row["area"]), str(row["kind"]), str(row["source_contract_id"])))
    return {
        "schema_version": PARITY_SCHEMA,
        "engine_version": engine_version,
        "source": {
            "blueprint_file": blueprint_file,
            "blueprint_sha256": blueprint_sha256,
            "blueprint_schema": manifest.get("blueprint_schema"),
            "conformance_contract_schema": manifest.get("schema_version"),
            "app_name": manifest.get("app_name"),
        },
        "authority": {
            "source_of_truth": "BLUEPRINT_EMBEDDED_CONFORMANCE_MANIFEST",
            "projection_only": True,
            "independent_specification": False,
            "candidate_self_report_has_authority": False,
            "runtime_equivalence_claimed": False,
            "visual_equivalence_claimed": False,
            "timing_equivalence_claimed": False,
        },
        "scenario_policy": {
            "required_mapped_contracts_only": True,
            "execution_class": "STATIC_RESCAN",
            "pass_condition": "SOURCE_CONTRACT_SATISFIED_BY_FRESH_SCAN",
            "runtime_scenarios_deferred_to_authorized_runtime_validation": True,
        },
        "scenario_count": len(scenarios),
        "scenarios": scenarios,
    }


def render_feature(report: dict[str, Any]) -> str:
    app = str((report.get("source") or {}).get("app_name") or "Application")
    blueprint = str((report.get("source") or {}).get("blueprint_file") or "Anchor Blueprint.md")
    lines = [
        f"Feature: {app} Anchor static parity",
        "  # Generated from the Blueprint's embedded conformance manifest.",
        "  # This file is a derived projection, not an independent specification.",
        "  # It establishes static rescan parity only; runtime/visual/timing equivalence is not claimed.",
        "",
    ]
    for row in report.get("scenarios") or []:
        tags = " ".join("@" + tag for tag in row.get("tags") or [])
        lines += [
            f"  {tags}",
            f"  Scenario: {row['source_contract_id']} {row.get('area')} {row.get('kind')}",
            f'    Given a reconstruction candidate based on "{blueprint}"',
            "    When SCAN performs a fresh read-only candidate scan and conformance comparison",
            f'    Then contract "{row["source_contract_id"]}" must be reported "SATISFIED"',
            "",
        ]
    return "\n".join(lines)


def render_agents_md(
    *,
    blueprint_file: str,
    blueprint_sha256: str,
    parity_json_sha256: str,
    parity_feature_sha256: str,
) -> str:
    return "\n".join([
        AGENTS_MARKER,
        "# SCAN / Anchor Agent Instructions",
        "",
        f"Primary reconstruction contract: {blueprint_file}",
        f"Blueprint SHA-256: {blueprint_sha256}",
        "",
        "Derived static parity aids:",
        f"- parity_scenarios.json SHA-256: {parity_json_sha256}",
        f"- parity_scenarios.feature SHA-256: {parity_feature_sha256}",
        "",
        "Rules:",
        "1. Read the Anchor Blueprint before modifying or reconstructing the candidate.",
        "2. The Blueprint's embedded SCAN conformance manifest is authoritative for static reconstruction contracts.",
        "3. parity_scenarios.json and parity_scenarios.feature are derived projections; they do not replace or extend the Blueprint.",
        "4. Candidate self-report is not evidence. Verify with a fresh SCAN conformance pass.",
        f'5. Verification command pattern: scan-body conform "{blueprint_file}" <candidate_root> --out <verification_dir>.',
        "6. Static parity does not establish runtime, visual/pixel, timing, network, or performance equivalence.",
        "7. Preserve PARTIAL, BLOCKED, and UNKNOWN uncertainty unless SCAN mechanically establishes stronger evidence.",
        "",
    ])


def write_parity_distribution(
    blueprint_path: Path,
    output_dir: Path | None = None,
    *,
    engine_version: str,
) -> dict[str, Any]:
    blueprint_path = Path(blueprint_path).resolve(strict=True)
    output_dir = Path(output_dir) if output_dir is not None else blueprint_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    blueprint_bytes = blueprint_path.read_bytes()
    blueprint_sha = _hash_bytes(blueprint_bytes)
    manifest = parse_blueprint_manifest(blueprint_path)
    report = build_parity_scenarios(
        manifest,
        blueprint_file=blueprint_path.name,
        blueprint_sha256=blueprint_sha,
        engine_version=engine_version,
    )

    json_path = output_dir / "parity_scenarios.json"
    feature_path = output_dir / "parity_scenarios.feature"
    agents_path = output_dir / "AGENTS.md"

    json_bytes = (json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    feature_bytes = render_feature(report).encode("utf-8")
    json_path.write_bytes(json_bytes)
    feature_path.write_bytes(feature_bytes)

    agents_text = render_agents_md(
        blueprint_file=blueprint_path.name,
        blueprint_sha256=blueprint_sha,
        parity_json_sha256=_hash_bytes(json_bytes),
        parity_feature_sha256=_hash_bytes(feature_bytes),
    )
    agents_state = "CREATED"
    if agents_path.exists():
        existing = agents_path.read_text(encoding="utf-8")
        if existing.startswith(AGENTS_MARKER):
            agents_state = "REFRESHED"
            agents_path.write_text(agents_text, encoding="utf-8")
        else:
            agents_state = "PRESERVED_EXISTING"
    else:
        agents_path.write_text(agents_text, encoding="utf-8")

    return {
        "schema_version": PARITY_SCHEMA,
        "state": "PASS",
        "scenario_count": report["scenario_count"],
        "source_blueprint": {
            "file": blueprint_path.name,
            "sha256": blueprint_sha,
        },
        "files": {
            "json": json_path.name,
            "feature": feature_path.name,
            "agents": agents_path.name if agents_state != "PRESERVED_EXISTING" else None,
        },
        "agents": {
            "state": agents_state,
            "path": agents_path.name,
            "existing_project_instructions_preserved": agents_state == "PRESERVED_EXISTING",
        },
        "sha256": {
            json_path.name: _hash_bytes(json_bytes),
            feature_path.name: _hash_bytes(feature_bytes),
            **({agents_path.name: _hash_bytes(agents_path.read_bytes())} if agents_state != "PRESERVED_EXISTING" else {}),
        },
    }
