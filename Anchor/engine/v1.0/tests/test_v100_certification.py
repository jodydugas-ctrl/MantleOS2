from __future__ import annotations

import json
from pathlib import Path
import shutil

from scan import __version__
from scan.release import write_package_manifest
from scan.v1_certification import (
    CI_REQUIRED_STAGES,
    V1_CERTIFICATE_NAME,
    V1_MANIFEST_NAME,
    V1_QUALIFICATION_NAME,
    certify_v1_local_release,
    verify_v1_local_certification,
)


def _copy_package(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[1]
    package = tmp_path / "package"
    shutil.copytree(
        source,
        package,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", ".pytest_cache"),
    )
    write_package_manifest(package)
    return package


def test_v1_local_release_certification_binds_exact_package_and_qualification(tmp_path: Path):
    package = _copy_package(tmp_path)
    out = tmp_path / "certification"

    result = certify_v1_local_release(package, out)

    assert result["state"] == "PASS"
    assert result["verification"]["state"] == "PASS"
    assert (out / V1_CERTIFICATE_NAME).is_file()
    assert (out / V1_QUALIFICATION_NAME).is_file()
    assert (out / V1_MANIFEST_NAME).is_file()

    certificate = json.loads((out / V1_CERTIFICATE_NAME).read_text(encoding="utf-8"))
    assert certificate["engine_version"] == "1.0.0"
    assert certificate["scope"] == "LOCAL_MECHANICAL_PACKAGE"
    assert certificate["package"]["audit_state"] == "PASS"
    assert certificate["package"]["manifest_sha256"]
    assert certificate["qualification"]["state"] == "PASS"
    assert certificate["release_authority"]["local_certificate_is_final_ci_certificate"] is False
    assert certificate["release_authority"]["ci_release_gate_required"] is True

    rows = {row["stage"]: row for row in certificate["roadmap"]}
    for stage in CI_REQUIRED_STAGES:
        assert rows[stage]["local_state"] == "NOT_ASSERTED_LOCALLY"
        assert rows[stage]["evidence_class"] == "CI_RELEASE_GATE_REQUIRED"


def test_v1_local_release_verifier_detects_certificate_tampering(tmp_path: Path):
    package = _copy_package(tmp_path)
    out = tmp_path / "certification"
    assert certify_v1_local_release(package, out)["state"] == "PASS"

    certificate = json.loads((out / V1_CERTIFICATE_NAME).read_text(encoding="utf-8"))
    certificate["state"] = "FAIL"
    (out / V1_CERTIFICATE_NAME).write_text(
        json.dumps(certificate, indent=2) + "\n",
        encoding="utf-8",
    )

    result = verify_v1_local_certification(out)
    assert result["state"] == "FAIL"
    assert any(issue["kind"] == "hash_mismatch" for issue in result["issues"])


def test_v1_local_release_verifier_rejects_untracked_file(tmp_path: Path):
    package = _copy_package(tmp_path)
    out = tmp_path / "certification"
    assert certify_v1_local_release(package, out)["state"] == "PASS"

    (out / "unexpected.txt").write_text("not sealed\n", encoding="utf-8")
    result = verify_v1_local_certification(out)
    assert result["state"] == "FAIL"
    assert any(issue["kind"] == "untracked_certification_file" for issue in result["issues"])


def test_v1_candidate_version():
    assert __version__ == "1.0.0"
