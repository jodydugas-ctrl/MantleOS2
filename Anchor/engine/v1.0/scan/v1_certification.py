from __future__ import annotations

"""Final v1.0 package-certification helpers.

This module deliberately separates a reproducible local mechanical certificate
from CI-wide release evidence. The local certificate can prove the exact package
bytes and the packaged SCAN qualification gate. Cross-platform, independent
reconstruction, live authorized-runtime, and operational-hardening evidence are
recorded by the release workflow and must not be inferred from this file alone.
"""

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any

from . import __version__
from .release import qualify_release, verify_package

V1_CERTIFICATE_SCHEMA = "scan-v1-local-release-certification/1.0"
V1_MANIFEST_SCHEMA = "scan-v1-local-release-manifest/1.0"
V1_CERTIFICATE_NAME = "v1_local_release_certificate.json"
V1_QUALIFICATION_NAME = "release_qualification.json"
V1_MANIFEST_NAME = "V1_RELEASE_MANIFEST.json"

ROADMAP = [
    "coverage_gaps",
    "uncertainty_challenger",
    "triage_ranking",
    "layered_provenance",
    "parity_scenarios_distribution",
    "broader_calibration",
    "independent_reconstruction_proof",
    "authorized_runtime_validation",
    "operational_hardening",
    "v1_certification",
]

QUALIFICATION_REEXECUTED_STAGES = {
    "coverage_gaps",
    "uncertainty_challenger",
    "triage_ranking",
    "layered_provenance",
    "v1_certification",
}

CI_REQUIRED_STAGES = {
    "parity_scenarios_distribution",
    "broader_calibration",
    "independent_reconstruction_proof",
    "authorized_runtime_validation",
    "operational_hardening",
}


def _safe_rel(value: str) -> str:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe certification path: {value!r}")
    return p.as_posix()


def _hash_file(path: Path) -> tuple[int, str]:
    h = sha256()
    size = 0
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            size += len(chunk)
            h.update(chunk)
    return size, h.hexdigest()


def _write_manifest(root: Path) -> dict[str, Any]:
    files = []
    for name in (V1_CERTIFICATE_NAME, V1_QUALIFICATION_NAME):
        path = root / name
        size, digest = _hash_file(path)
        files.append({"path": name, "bytes": size, "sha256": digest})
    payload = {
        "schema_version": V1_MANIFEST_SCHEMA,
        "engine_version": __version__,
        "files": files,
    }
    (root / V1_MANIFEST_NAME).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def verify_v1_local_certification(certification_root: Path) -> dict[str, Any]:
    root = Path(certification_root).resolve(strict=True)
    issues: list[dict[str, Any]] = []
    manifest_path = root / V1_MANIFEST_NAME
    certificate_path = root / V1_CERTIFICATE_NAME
    qualification_path = root / V1_QUALIFICATION_NAME

    if not manifest_path.is_file():
        return {
            "schema_version": "scan-v1-local-release-verification/1.0",
            "state": "FAIL",
            "issues": [{"kind": "missing_v1_manifest"}],
        }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {
            "schema_version": "scan-v1-local-release-verification/1.0",
            "state": "FAIL",
            "issues": [{"kind": "invalid_v1_manifest", "error": str(exc)}],
        }

    if manifest.get("schema_version") != V1_MANIFEST_SCHEMA:
        issues.append({"kind": "unsupported_manifest_schema", "value": manifest.get("schema_version")})
    if manifest.get("engine_version") != __version__:
        issues.append({
            "kind": "engine_version_mismatch",
            "manifest": manifest.get("engine_version"),
            "runtime": __version__,
        })

    expected: set[str] = set()
    for item in manifest.get("files", []):
        try:
            rel = _safe_rel(str(item["path"]))
        except Exception as exc:
            issues.append({"kind": "unsafe_manifest_path", "item": item, "error": str(exc)})
            continue
        expected.add(rel)
        path = root.joinpath(*PurePosixPath(rel).parts)
        if not path.is_file():
            issues.append({"kind": "missing_certification_file", "path": rel})
            continue
        size, digest = _hash_file(path)
        if size != int(item.get("bytes", -1)):
            issues.append({"kind": "size_mismatch", "path": rel})
        if digest != item.get("sha256"):
            issues.append({"kind": "hash_mismatch", "path": rel})

    actual = {
        p.relative_to(root).as_posix()
        for p in root.iterdir()
        if p.is_file() and p.name != V1_MANIFEST_NAME
    }
    for rel in sorted(actual - expected):
        issues.append({"kind": "untracked_certification_file", "path": rel})

    certificate: dict[str, Any] = {}
    qualification: dict[str, Any] = {}
    try:
        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        if certificate.get("schema_version") != V1_CERTIFICATE_SCHEMA:
            issues.append({"kind": "unsupported_certificate_schema", "value": certificate.get("schema_version")})
        if certificate.get("state") != "PASS":
            issues.append({"kind": "certificate_not_pass", "value": certificate.get("state")})
        if certificate.get("scope") != "LOCAL_MECHANICAL_PACKAGE":
            issues.append({"kind": "unexpected_certificate_scope", "value": certificate.get("scope")})
    except Exception as exc:
        issues.append({"kind": "invalid_certificate", "error": str(exc)})

    try:
        qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
        if qualification.get("state") != "PASS":
            issues.append({"kind": "qualification_not_pass", "value": qualification.get("state")})
    except Exception as exc:
        issues.append({"kind": "invalid_qualification", "error": str(exc)})

    return {
        "schema_version": "scan-v1-local-release-verification/1.0",
        "state": "PASS" if not issues else "FAIL",
        "engine_version": __version__,
        "certificate_state": certificate.get("state"),
        "qualification_state": qualification.get("state"),
        "issue_count": len(issues),
        "issues": issues,
    }


def certify_v1_local_release(package_root: Path, certification_root: Path) -> dict[str, Any]:
    if __version__ != "1.0.0":
        raise RuntimeError(f"v1 certification requires engine version 1.0.0, got {__version__}")

    package = Path(package_root).resolve(strict=True)
    out = Path(certification_root).resolve()
    out.mkdir(parents=True, exist_ok=True)

    package_audit = verify_package(package)
    qualification_path = out / V1_QUALIFICATION_NAME
    qualification = qualify_release(package, output_path=qualification_path)

    manifest_path = package / "PACKAGE_MANIFEST.json"
    package_manifest_size, package_manifest_sha256 = (
        _hash_file(manifest_path) if manifest_path.is_file() else (0, None)
    )
    qualification_size, qualification_sha256 = _hash_file(qualification_path)

    roadmap = []
    for stage in ROADMAP:
        if stage in QUALIFICATION_REEXECUTED_STAGES:
            evidence = "REEXECUTED_LOCAL_MECHANICAL_GATE"
            local_state = "PASS" if qualification.get("state") == "PASS" else "FAIL"
        elif stage in CI_REQUIRED_STAGES:
            evidence = "CI_RELEASE_GATE_REQUIRED"
            local_state = "NOT_ASSERTED_LOCALLY"
        else:
            evidence = "UNKNOWN"
            local_state = "UNKNOWN"
        roadmap.append({
            "stage": stage,
            "local_state": local_state,
            "evidence_class": evidence,
        })

    local_pass = package_audit.get("state") == "PASS" and qualification.get("state") == "PASS"
    certificate = {
        "schema_version": V1_CERTIFICATE_SCHEMA,
        "engine_version": __version__,
        "state": "PASS" if local_pass else "FAIL",
        "scope": "LOCAL_MECHANICAL_PACKAGE",
        "meaning": (
            "PASS binds the exact package manifest to a successful packaged mechanical qualification. "
            "It does not by itself assert CI-only cross-platform, independent-reconstruction, live-runtime, "
            "or operational-hardening release gates."
        ),
        "package": {
            "audit_state": package_audit.get("state"),
            "manifest_bytes": package_manifest_size,
            "manifest_sha256": package_manifest_sha256,
            "manifest_file_count": package_audit.get("manifest_file_count"),
            "verified_file_count": package_audit.get("verified_file_count"),
        },
        "qualification": {
            "state": qualification.get("state"),
            "bytes": qualification_size,
            "sha256": qualification_sha256,
            "schema_version": qualification.get("schema_version"),
        },
        "roadmap": roadmap,
        "release_authority": {
            "local_certificate_is_final_ci_certificate": False,
            "ci_release_gate_required": True,
            "coverage_completeness_implied": False,
            "runtime_equivalence_implied": False,
            "hostile_code_sandbox_implied": False,
        },
    }
    (out / V1_CERTIFICATE_NAME).write_text(
        json.dumps(certificate, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    manifest = _write_manifest(out)
    verification = verify_v1_local_certification(out)

    return {
        "schema_version": "scan-v1-local-release-certification-run/1.0",
        "state": "PASS" if local_pass and verification.get("state") == "PASS" else "FAIL",
        "certificate": certificate,
        "manifest": manifest,
        "verification": verification,
        "certification_root": str(out),
    }
