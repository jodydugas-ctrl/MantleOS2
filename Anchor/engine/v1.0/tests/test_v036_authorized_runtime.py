from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

import pytest

import scan.runtime_validation as runtime_validation
from scan import __version__
from scan.runtime_validation import (
    RUNTIME_PLAN_SCHEMA,
    load_runtime_plan,
    plan_sha256,
    run_authorized_runtime_validation,
)


def _write_fixture(root: Path) -> None:
    root.mkdir()
    (root / "app.py").write_text(
        """import json
from pathlib import Path
print("READY")
Path("state.json").write_text(json.dumps({"saved": True, "count": 3}) + "\\n", encoding="utf-8")
""",
        encoding="utf-8",
    )


def _write_plan(path: Path, *, network: str = "DENY") -> dict:
    plan = {
        "schema_version": RUNTIME_PLAN_SCHEMA,
        "plan_id": "runtime-fixture-save",
        "network": network,
        "command": ["python3", "app.py"],
        "cwd": ".",
        "timeout_seconds": 5,
        "max_output_bytes": 32768,
        "source_refs": ["AC-STATIC-001", "PS-STATIC-001"],
        "assertions": [
            {"id": "exit", "kind": "EXIT_CODE_EQUALS", "equals": 0},
            {"id": "ready", "kind": "STDOUT_CONTAINS", "value": "READY"},
            {"id": "persisted", "kind": "FILE_EXISTS", "path": "state.json"},
            {
                "id": "saved-state",
                "kind": "JSON_POINTER_EQUALS",
                "path": "state.json",
                "pointer": "/saved",
                "equals": True,
                "source_refs": ["AC-STATIC-001"],
            },
            {
                "id": "count-state",
                "kind": "JSON_POINTER_EQUALS",
                "path": "state.json",
                "pointer": "/count",
                "equals": 3,
            },
            {"id": "time", "kind": "DURATION_MS_MAX", "max": 5000},
        ],
    }
    path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return plan


def _tree_hash(root: Path) -> str:
    records = []
    for item in sorted(p for p in root.rglob("*") if p.is_file()):
        records.append(
            (
                item.relative_to(root).as_posix(),
                sha256(item.read_bytes()).hexdigest(),
            )
        )
    return sha256(json.dumps(records).encode("utf-8")).hexdigest()


def test_plan_requires_network_deny(tmp_path: Path):
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path, network="ALLOW")
    with pytest.raises(ValueError, match="network=DENY"):
        load_runtime_plan(plan_path)


def test_wrong_plan_hash_blocks_before_network_or_execution(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    _write_fixture(target)
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path)

    def should_not_run():
        raise AssertionError("network preflight must not run before authorization succeeds")

    monkeypatch.setattr(runtime_validation, "_network_prefix", should_not_run)
    before = _tree_hash(target)
    report = run_authorized_runtime_validation(
        target,
        plan_path,
        tmp_path / "out",
        authorized_plan_sha256="0" * 64,
    )
    assert report["state"] == "BLOCKED"
    assert report["reason"] == "PLAN_NOT_AUTHORIZED"
    assert report["authorization"]["matched"] is False
    assert _tree_hash(target) == before
    assert (tmp_path / "out" / "runtime_validation.json").is_file()


def test_authorized_runtime_uses_temp_copy_and_preserves_static_target(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    _write_fixture(target)
    plan_path = tmp_path / "plan.json"
    _write_plan(plan_path)

    monkeypatch.setattr(
        runtime_validation,
        "_network_prefix",
        lambda: (
            [],
            {
                "state": "PASS",
                "mechanism": "TEST_NETWORK_ISOLATION",
                "interfaces": ["lo"],
            },
        ),
    )

    before = _tree_hash(target)
    report = run_authorized_runtime_validation(
        target,
        plan_path,
        tmp_path / "out",
        authorized_plan_sha256=plan_sha256(plan_path),
    )
    after = _tree_hash(target)

    assert report["state"] == "PASS"
    assert report["authorization"]["matched"] is True
    assert report["plan_id"] == "runtime-fixture-save"
    assert report["source_refs"] == ["AC-STATIC-001", "PS-STATIC-001"]
    assert report["isolation"]["working_copy"] == "TEMPORARY_COPY"
    assert report["isolation"]["shell"] is False
    assert report["isolation"]["environment"] == "SANITIZED"
    assert report["source_integrity"]["unchanged"] is True
    assert before == after
    assert not (target / "state.json").exists()
    assert report["workspace"]["changed"] is True
    assert report["workspace"]["retained"] is False
    assert report["process"]["returncode"] == 0
    assert report["process"]["timed_out"] is False
    assert "READY" in report["process"]["stdout"]
    assert report["assertion_count"] == 6
    assert report["assertion_failures"] == 0
    assert all(row["state"] == "PASS" for row in report["assertions"])
    assert report["authority"] == {
        "runtime_observation_only": True,
        "static_store_mutated": False,
        "automatic_promotion": False,
        "ordinary_scan_execution_changed": False,
        "runtime_result_may_override_static_uncertainty": False,
    }
    saved = next(row for row in report["assertions"] if row["id"] == "saved-state")
    assert saved["source_refs"] == ["AC-STATIC-001"]


def test_failed_runtime_assertion_is_evidence_not_promotion(tmp_path: Path, monkeypatch):
    target = tmp_path / "target"
    _write_fixture(target)
    plan_path = tmp_path / "plan.json"
    plan = _write_plan(plan_path)
    plan["assertions"].append(
        {
            "id": "false-claim",
            "kind": "JSON_POINTER_EQUALS",
            "path": "state.json",
            "pointer": "/count",
            "equals": 999,
        }
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        runtime_validation,
        "_network_prefix",
        lambda: ([], {"state": "PASS", "mechanism": "TEST_NETWORK_ISOLATION", "interfaces": ["lo"]}),
    )
    report = run_authorized_runtime_validation(
        target,
        plan_path,
        tmp_path / "out",
        authorized_plan_sha256=plan_sha256(plan_path),
    )
    assert report["state"] == "FAIL"
    assert report["assertion_failures"] == 1
    failed = next(row for row in report["assertions"] if row["id"] == "false-claim")
    assert failed["state"] == "FAIL"
    assert failed["actual"] == 3
    assert report["authority"]["automatic_promotion"] is False
    assert report["authority"]["runtime_result_may_override_static_uncertainty"] is False


def test_unsafe_runtime_paths_are_rejected(tmp_path: Path):
    target = tmp_path / "target"
    _write_fixture(target)
    plan_path = tmp_path / "plan.json"
    plan = _write_plan(plan_path)
    plan["assertions"].append(
        {"id": "escape", "kind": "FILE_EXISTS", "path": "../outside.txt"}
    )
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    report = run_authorized_runtime_validation(
        target,
        plan_path,
        tmp_path / "out",
        authorized_plan_sha256=plan_sha256(plan_path),
    )
    assert report["state"] == "BLOCKED"
    assert report["reason"] == "INVALID_PLAN"
    assert "unsafe relative path" in report["error"]



def test_ordinary_scan_never_executes_runtime_target(tmp_path: Path):
    from scan.engine import ScanEngine

    target = tmp_path / "ordinary"
    target.mkdir()
    (target / "danger.py").write_text(
        'from pathlib import Path\nPath("EXECUTED").write_text("bad", encoding="utf-8")\n',
        encoding="utf-8",
    )
    out = tmp_path / "scan"
    ScanEngine().scan(target, out, "v036-no-runtime")
    assert not (target / "EXECUTED").exists()
    assert not (out / "runtime_validation.json").exists()
    assert not (out / "runtime_validation.md").exists()

def test_inherited_runtime_validation_runs_under_current_candidate():
    assert __version__ == "0.37.0"
