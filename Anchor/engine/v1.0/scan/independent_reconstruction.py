from __future__ import annotations

"""Mechanical verification for independently isolated reconstruction trials.

This module does not reconstruct software and does not judge source similarity.
It verifies that a candidate came through a source-isolated worker handoff and
that the existing private SCAN reconstruction scorer independently rescanned it.
"""

from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
from typing import Any

from .reconstruction_trial import CHALLENGE_MANIFEST, SUBMISSION_SCHEMA, verify_reconstruction_trial

WORKER_RECEIPT_SCHEMA = "scan-independent-worker-receipt/0.1"
PROOF_SCHEMA = "scan-independent-reconstruction-proof/0.1"
CHALLENGE_MANIFEST_SCHEMA = "scan-reconstruction-challenge-manifest/0.1"

ENFORCED_NETWORK_STATES = {
    "ENFORCED_LINUX_NETWORK_NAMESPACE",
    "ENFORCED_CONTAINER_NO_NETWORK",
}


def _json(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _hash_file(path: Path) -> str:
    h = sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_rel(value: str) -> str:
    p = PurePosixPath(value)
    if not value or p.is_absolute() or ".." in p.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return p.as_posix()


def tree_records(root: Path) -> list[dict[str, Any]]:
    root = Path(root).resolve(strict=True)
    records = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        records.append({
            "path": rel,
            "bytes": path.stat().st_size,
            "sha256": _hash_file(path),
        })
    return records


def tree_digest(root: Path) -> tuple[int, str]:
    records = tree_records(root)
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return len(records), sha256(canonical.encode("utf-8")).hexdigest()


def verify_public_challenge(challenge_root: Path) -> dict[str, Any]:
    root = Path(challenge_root).resolve(strict=True)
    manifest_path = root / CHALLENGE_MANIFEST
    issues: list[dict[str, Any]] = []
    if not manifest_path.is_file():
        return {"state": "FAIL", "issues": [{"kind": "missing_challenge_manifest"}]}

    try:
        manifest = _json(manifest_path)
    except Exception as exc:
        return {"state": "FAIL", "issues": [{"kind": "invalid_challenge_manifest", "error": str(exc)}]}

    if manifest.get("schema_version") != CHALLENGE_MANIFEST_SCHEMA:
        issues.append({
            "kind": "challenge_manifest_schema",
            "expected": CHALLENGE_MANIFEST_SCHEMA,
            "actual": manifest.get("schema_version"),
        })

    expected: set[str] = set()
    for item in manifest.get("files") or []:
        try:
            rel = _safe_rel(str(item["path"]))
        except Exception as exc:
            issues.append({"kind": "unsafe_manifest_path", "item": item, "error": str(exc)})
            continue
        expected.add(rel)
        path = root.joinpath(*PurePosixPath(rel).parts)
        if not path.is_file():
            issues.append({"kind": "missing_challenge_file", "path": rel})
            continue
        if path.stat().st_size != int(item.get("bytes", -1)):
            issues.append({"kind": "challenge_size_mismatch", "path": rel})
        if _hash_file(path) != item.get("sha256"):
            issues.append({"kind": "challenge_hash_mismatch", "path": rel})

    actual = {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.name != CHALLENGE_MANIFEST
    }
    for rel in sorted(actual - expected):
        issues.append({"kind": "untracked_challenge_file", "path": rel})

    forbidden_names = {
        "scan_index.sqlite",
        "evidence_catalog.json",
        "evidence_graph.json",
        "machine_body_map.json",
        "evaluator.json",
        "EVALUATOR_MANIFEST.json",
    }
    leaked = sorted(p.name for p in root.rglob("*") if p.is_file() and p.name in forbidden_names)
    if leaked:
        issues.append({"kind": "forbidden_private_artifact", "files": leaked})

    return {
        "state": "PASS" if not issues else "FAIL",
        "manifest_sha256": _hash_file(manifest_path),
        "manifest_file_count": len(manifest.get("files") or []),
        "issue_count": len(issues),
        "issues": issues,
    }


def verify_worker_receipt(
    challenge_root: Path,
    candidate_root: Path,
    submission_path: Path,
    receipt_path: Path,
) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    challenge = verify_public_challenge(challenge_root)
    if challenge.get("state") != "PASS":
        issues.append({"kind": "challenge_invalid", "details": challenge.get("issues")})

    try:
        receipt = _json(receipt_path)
    except Exception as exc:
        return {
            "schema_version": "scan-independent-worker-verification/0.1",
            "state": "FAIL",
            "issue_count": 1,
            "issues": [{"kind": "invalid_worker_receipt", "error": str(exc)}],
        }

    if receipt.get("schema_version") != WORKER_RECEIPT_SCHEMA:
        issues.append({
            "kind": "worker_receipt_schema",
            "expected": WORKER_RECEIPT_SCHEMA,
            "actual": receipt.get("schema_version"),
        })

    if receipt.get("challenge_manifest_sha256") != challenge.get("manifest_sha256"):
        issues.append({"kind": "challenge_manifest_hash_mismatch"})

    candidate_count, candidate_digest = tree_digest(candidate_root)
    if receipt.get("candidate_tree_sha256") != candidate_digest:
        issues.append({"kind": "candidate_tree_hash_mismatch"})
    if int(receipt.get("candidate_file_count", -1)) != candidate_count:
        issues.append({"kind": "candidate_file_count_mismatch"})

    submission_path = Path(submission_path).resolve(strict=True)
    if receipt.get("submission_sha256") != _hash_file(submission_path):
        issues.append({"kind": "submission_hash_mismatch"})
    try:
        submission = _json(submission_path)
    except Exception as exc:
        submission = {}
        issues.append({"kind": "invalid_submission", "error": str(exc)})
    if submission.get("schema_version") != SUBMISSION_SCHEMA:
        issues.append({"kind": "submission_schema_mismatch"})

    isolation = receipt.get("isolation") or {}
    if isolation.get("repository_checkout") != "ABSENT":
        issues.append({"kind": "repository_checkout_not_absent"})
    if isolation.get("original_source") != "NOT_PRESENT":
        issues.append({"kind": "original_source_not_absent"})
    if isolation.get("private_evaluator") != "NOT_PRESENT":
        issues.append({"kind": "private_evaluator_not_absent"})
    if isolation.get("input_artifacts") != ["challenge"]:
        issues.append({"kind": "unexpected_worker_input_artifacts", "actual": isolation.get("input_artifacts")})
    if isolation.get("network_during_worker") not in ENFORCED_NETWORK_STATES:
        issues.append({
            "kind": "network_isolation_not_enforced",
            "actual": isolation.get("network_during_worker"),
        })

    submission_isolation = submission.get("source_isolation") or {}
    for key in (
        "original_source_accessed",
        "parent_certification_accessed",
        "evaluator_bundle_accessed",
        "network_source_lookup_used",
    ):
        if submission_isolation.get(key) is not False:
            issues.append({"kind": "submission_source_isolation_failed", "field": key})

    return {
        "schema_version": "scan-independent-worker-verification/0.1",
        "state": "PASS" if not issues else "FAIL",
        "challenge_manifest_sha256": challenge.get("manifest_sha256"),
        "candidate_tree_sha256": candidate_digest,
        "candidate_file_count": candidate_count,
        "worker": receipt.get("worker") or {},
        "isolation": isolation,
        "issue_count": len(issues),
        "issues": issues,
    }


def verify_independent_reconstruction_proof(
    challenge_root: Path,
    candidate_root: Path,
    submission_path: Path,
    worker_receipt_path: Path,
    trial_root: Path,
    *,
    output_path: Path | None = None,
    reference_worker: bool = False,
) -> dict[str, Any]:
    worker = verify_worker_receipt(
        challenge_root, candidate_root, submission_path, worker_receipt_path,
    )
    trial = verify_reconstruction_trial(trial_root)
    issues: list[dict[str, Any]] = []

    if worker.get("state") != "PASS":
        issues.append({"kind": "worker_isolation_or_lineage_invalid", "details": worker.get("issues")})
    if trial.get("state") != "PASS":
        issues.append({"kind": "trial_verification_failed", "details": trial.get("issues")})

    challenge_json = _json(Path(challenge_root) / "challenge.json")
    trial_receipt = _json(Path(trial_root) / "trial_receipt.json")
    scorecard = _json(Path(trial_root) / "scorecard.json")
    submission = _json(Path(submission_path))

    challenge_id = challenge_json.get("challenge_id")
    if trial_receipt.get("challenge_id") != challenge_id:
        issues.append({"kind": "trial_challenge_id_mismatch"})
    if scorecard.get("challenge_id") != challenge_id:
        issues.append({"kind": "scorecard_challenge_id_mismatch"})
    if (trial_receipt.get("lineage") or {}).get("challenge_manifest_sha256") != worker.get("challenge_manifest_sha256"):
        issues.append({"kind": "trial_challenge_lineage_mismatch"})

    declared_enforcement = (submission.get("source_isolation") or {}).get("enforcement_level")
    recorded_enforcement = (trial_receipt.get("blindness") or {}).get("agent_isolation")
    if declared_enforcement != recorded_enforcement:
        issues.append({
            "kind": "isolation_enforcement_receipt_mismatch",
            "submission": declared_enforcement,
            "trial": recorded_enforcement,
        })

    trial_state = str(scorecard.get("state") or "INVALID")
    if issues:
        state = "INVALID"
    elif trial_state == "PASS":
        state = "PASS"
    elif trial_state == "PARTIAL":
        state = "PARTIAL"
    else:
        state = "FAIL"

    report = {
        "schema_version": PROOF_SCHEMA,
        "engine_version": trial_receipt.get("engine_version"),
        "state": state,
        "challenge_id": challenge_id,
        "independence": {
            "state": worker.get("state"),
            "repository_checkout": (worker.get("isolation") or {}).get("repository_checkout"),
            "original_source": (worker.get("isolation") or {}).get("original_source"),
            "private_evaluator": (worker.get("isolation") or {}).get("private_evaluator"),
            "network_during_worker": (worker.get("isolation") or {}).get("network_during_worker"),
            "input_artifacts": (worker.get("isolation") or {}).get("input_artifacts"),
        },
        "lineage": {
            "challenge_manifest_sha256": worker.get("challenge_manifest_sha256"),
            "candidate_tree_sha256": worker.get("candidate_tree_sha256"),
            "trial_challenge_manifest_sha256": (trial_receipt.get("lineage") or {}).get("challenge_manifest_sha256"),
            "evaluator_manifest_sha256": (trial_receipt.get("lineage") or {}).get("evaluator_manifest_sha256"),
        },
        "adjudication": {
            "trial_verification_state": trial.get("state"),
            "score_state": trial_state,
            "anchor_counts": scorecard.get("anchor_counts") or {},
            "fidelity_score": scorecard.get("fidelity_score"),
            "candidate_self_report_authority": "NONE",
            "measurement_authority": "FRESH_SCAN_PRIVATE_EVALUATOR",
        },
        "claims": {
            "static_reconstruction_proof": state == "PASS",
            "runtime_equivalence_claimed": False,
            "visual_equivalence_claimed": False,
            "timing_equivalence_claimed": False,
            "external_llm_benchmark_claimed": False,
            "reference_worker": bool(reference_worker),
        },
        "worker_verification": worker,
        "trial_verification": trial,
        "issue_count": len(issues),
        "issues": issues,
    }

    if output_path is not None:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return report
