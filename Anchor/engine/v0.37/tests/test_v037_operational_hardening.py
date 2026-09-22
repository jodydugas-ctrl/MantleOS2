from __future__ import annotations

import json
import os
from pathlib import Path
import platform

import pytest

from scan import __version__
from scan.engine import ScanEngine
from scan.operational_hardening import (
    OUTPUT_LEASE_NAME,
    OUTPUT_LEASE_SCHEMA,
    OutputBusyError,
    OutputLease,
    UnsafeOutputPathError,
    inspect_output_lease,
)


class _FatalAdapter:
    name = "fatal-test"
    version = "1"

    def accepts(self, rec):
        return rec.path.endswith(".txt")

    def cache_version(self, content_root, rec):
        return self.version

    def extract(self, content_root, rec, text):
        raise MemoryError("synthetic catastrophic parser failure")


def _simple_specimen(root: Path) -> Path:
    root.mkdir()
    (root / "a.cpp").write_text("void a(){}\n", encoding="utf-8")
    (root / "notes.txt").write_text("hello\n", encoding="utf-8")
    return root


def test_output_lease_refuses_concurrent_writer_and_cleans_up(tmp_path: Path):
    out = tmp_path / "out"
    with OutputLease(out, engine_version=__version__):
        state = inspect_output_lease(out)
        assert state["state"] == "ACTIVE_SAME_HOST"
        with pytest.raises(OutputBusyError, match="already leased"):
            with OutputLease(out, engine_version=__version__):
                pass
    assert inspect_output_lease(out)["state"] == "FREE"
    assert not (out / OUTPUT_LEASE_NAME).exists()


def test_dead_same_host_lease_is_recovered(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    (out / OUTPUT_LEASE_NAME).write_text(
        json.dumps(
            {
                "schema_version": OUTPUT_LEASE_SCHEMA,
                "engine_version": "old",
                "pid": 2_147_483_000,
                "host": platform.node() or "UNKNOWN_HOST",
                "started_ns": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert inspect_output_lease(out)["state"] == "STALE_SAME_HOST"
    with OutputLease(out, engine_version=__version__):
        assert inspect_output_lease(out)["state"] == "ACTIVE_SAME_HOST"
    assert inspect_output_lease(out)["state"] == "FREE"


def test_foreign_or_unreadable_lease_fails_closed(tmp_path: Path):
    out = tmp_path / "out"
    out.mkdir()
    lock = out / OUTPUT_LEASE_NAME
    lock.write_text(
        json.dumps(
            {
                "schema_version": OUTPUT_LEASE_SCHEMA,
                "engine_version": __version__,
                "pid": os.getpid(),
                "host": "foreign-host-that-cannot-be-proved-stale",
                "started_ns": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(OutputBusyError):
        OutputLease(out, engine_version=__version__).acquire()

    lock.write_bytes(b"not-json\xff")
    assert inspect_output_lease(out)["state"] == "BLOCKED_UNKNOWN"
    with pytest.raises(OutputBusyError):
        OutputLease(out, engine_version=__version__).acquire()


def test_fatal_parser_failure_propagates_but_releases_output_lease(tmp_path: Path):
    specimen = tmp_path / "specimen"
    specimen.mkdir()
    (specimen / "fatal.txt").write_text("trigger\n", encoding="utf-8")
    out = tmp_path / "out"

    with pytest.raises(MemoryError, match="synthetic catastrophic"):
        ScanEngine(adapters=[_FatalAdapter()]).scan(specimen, out, "fatal-hardening")

    assert inspect_output_lease(out)["state"] == "FREE"
    assert not (out / OUTPUT_LEASE_NAME).exists()


def test_malformed_bytes_are_accounted_without_crashing_or_escaping(tmp_path: Path):
    specimen = tmp_path / "specimen"
    specimen.mkdir()
    corpus = {
        "broken.cpp": b"\xff\xfe\x00class { {{{\n",
        "broken.ui": b"<ui><widget><broken>\xff",
        "broken.cmake": b"project(\xff\xfe",
        "broken.txt": b"\x00\x01\x02\xff\n",
    }
    for name, payload in corpus.items():
        (specimen / name).write_bytes(payload)

    out = tmp_path / "out"
    summary = ScanEngine().scan(specimen, out, "malformed-corpus")

    assert summary["inventory"]["file_count"] == len(corpus)
    assert {row["path"] for row in summary["files"]} == set(corpus)
    assert all(".." not in Path(row["path"]).parts for row in summary["files"])
    assert inspect_output_lease(out)["state"] == "FREE"
    assert (out / "projection_manifest.json").is_file()


def test_large_visible_repository_degrades_explicitly_under_materialization_budget(tmp_path: Path):
    specimen = tmp_path / "large"
    specimen.mkdir()
    for i in range(300):
        (specimen / f"f{i:04d}.cpp").write_text(f"void f{i}(){{}}\n", encoding="utf-8")

    summary = ScanEngine(max_materialized_files=25).scan(
        specimen, tmp_path / "out", "large-budget-envelope"
    )

    assert summary["inventory"]["file_count"] == 300
    assert summary["inventory"]["materialized_file_count"] == 25
    assert summary["inventory"]["acquisition_counts"]["RESOURCE_LIMIT_TOTAL_FILES"] == 275
    assert summary["budget"]["triggered"] is True
    assert summary["budget"]["inventory_limit_states"]["RESOURCE_LIMIT_TOTAL_FILES"] == 275


def test_manifest_path_traversal_is_rejected_before_output_creation(tmp_path: Path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "scan-source-manifest/0.1",
                "specimen": {"provider": "test"},
                "files": [{"path": "../escape.cpp", "size": 1}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    with pytest.raises(ValueError, match="unsafe manifest path"):
        ScanEngine().scan_manifest(manifest, out, specimen_id="traversal")
    assert not out.exists()


def test_output_root_symlink_is_rejected(tmp_path: Path):
    if not hasattr(os, "symlink"):
        pytest.skip("symlink unavailable")
    real = tmp_path / "real-output"
    real.mkdir()
    alias = tmp_path / "alias-output"
    try:
        os.symlink(real, alias, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation unavailable: {exc}")
    with pytest.raises(UnsafeOutputPathError, match="must not be a symlink"):
        OutputLease(alias, engine_version=__version__).acquire()


def test_candidate_version_is_v037():
    assert __version__ == "0.37.0"
