from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import tempfile

from scan import __version__
from scan.independent_reconstruction import (
    WORKER_RECEIPT_SCHEMA,
    tree_digest,
    verify_public_challenge,
    verify_worker_receipt,
    verify_independent_reconstruction_proof,
)
from scan.reconstruction_trial import (
    CHALLENGE_MANIFEST,
    SUBMISSION_SCHEMA,
    prepare_reconstruction_trial,
    score_reconstruction_trial,
)
from scan.release import (
    certify_reconstruction_handoff,
    certify_specimen,
    write_package_manifest,
)
from scan.store import Store


UI = """<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainWindow</class>
 <widget class="QMainWindow" name="MainWindow">
  <action name="actionSave"><property name="text"><string>Save</string></property></action>
 </widget>
</ui>
"""

CPP = """#include <QAction>
void MainWindow::wire() {
    connect(ui->actionSave, &QAction::triggered, this, &MainWindow::saveFile);
}
void MainWindow::saveFile() {}
"""


def _proposal(save_id: str) -> dict:
    return {
        "schema_version": "scan-reconstruction-proposal/0.1",
        "proposal_id": "RP-V035-SAVE",
        "objects": [
            {
                "id": "BEH-V035-SAVE",
                "object_type": "BEHAVIOR",
                "subtype": "document-save",
                "label": "Save current document",
                "coverage": "MAPPED",
                "attributes": {
                    "trigger": "User invokes Save",
                    "observable_response": "The Save route reaches the recovered save handler",
                    "uncertainty": "Only the recovered static route is asserted",
                },
            },
            {
                "id": "RA-V035-SAVE",
                "object_type": "RECONSTRUCTION_ANCHOR",
                "subtype": "behavior",
                "label": "Preserve Save semantics",
                "coverage": "MAPPED",
                "attributes": {
                    "property": "A human-facing Save control must reach the save behavior.",
                    "fidelity_test": "Invoke Save and verify the control reaches the save behavior.",
                    "uncertainty": "Runtime persistence details are outside this fixture.",
                },
            },
        ],
        "relations": [
            {"src": save_id, "dst": "BEH-V035-SAVE", "kind": "supports"},
            {"src": "BEH-V035-SAVE", "dst": "RA-V035-SAVE", "kind": "supports_anchor"},
        ],
    }


def _sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _submission(path: Path, challenge_id: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema_version": SUBMISSION_SCHEMA,
                "challenge_id": challenge_id,
                "agent": {
                    "name": "deterministic-reference-worker",
                    "version": "1",
                    "provider": "SCAN-CI",
                },
                "source_isolation": {
                    "original_source_accessed": False,
                    "parent_certification_accessed": False,
                    "evaluator_bundle_accessed": False,
                    "network_source_lookup_used": False,
                    "enforcement_level": "CI_SEPARATE_JOB_NETWORK_NAMESPACE",
                },
                "notes": "independent-proof verifier regression",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _worker_receipt(path: Path, challenge: Path, candidate: Path, submission: Path, **isolation_overrides) -> Path:
    count, digest = tree_digest(candidate)
    isolation = {
        "repository_checkout": "ABSENT",
        "original_source": "NOT_PRESENT",
        "private_evaluator": "NOT_PRESENT",
        "input_artifacts": ["challenge"],
        "network_during_worker": "ENFORCED_LINUX_NETWORK_NAMESPACE",
    }
    isolation.update(isolation_overrides)
    path.write_text(
        json.dumps(
            {
                "schema_version": WORKER_RECEIPT_SCHEMA,
                "challenge_manifest_sha256": _sha(challenge / CHALLENGE_MANIFEST),
                "candidate_tree_sha256": digest,
                "candidate_file_count": count,
                "submission_sha256": _sha(submission),
                "worker": {
                    "kind": "deterministic-reference",
                    "name": "fixture-worker",
                    "implementation_sha256": "0" * 64,
                },
                "isolation": isolation,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _prepared_trial(td: Path):
    package = Path(__file__).resolve().parents[1]
    write_package_manifest(package)

    source = td / "private-source"
    source.mkdir()
    (source / "MainWindow.ui").write_text(UI, encoding="utf-8")
    (source / "MainWindow.cpp").write_text(CPP, encoding="utf-8")

    mechanical = td / "mechanical"
    assert certify_specimen(package, source, mechanical, specimen_id="v035-private-source")["state"] == "PASS"

    store = Store(mechanical / "scan" / "scan_index.sqlite", readonly=True)
    try:
        save = next(row for row in store.semantic_objects() if row["label"] == "actionSave")
    finally:
        store.close()

    proposal = td / "proposal.json"
    proposal.write_text(json.dumps(_proposal(save["id"])), encoding="utf-8")

    semantic = td / "semantic"
    assert certify_reconstruction_handoff(package, mechanical, proposal, semantic)["state"] == "PASS"

    challenge = td / "challenge"
    evaluator = td / "evaluator"
    prepared = prepare_reconstruction_trial(semantic, challenge, evaluator)
    assert prepared["state"] == "PASS"

    candidate = td / "candidate"
    candidate.mkdir()
    (candidate / "MainWindow.ui").write_text(UI, encoding="utf-8")
    (candidate / "MainWindow.cpp").write_text(CPP, encoding="utf-8")

    submission = _submission(td / "submission.json", prepared["challenge_id"])
    receipt = _worker_receipt(td / "worker_receipt.json", challenge, candidate, submission)
    return package, challenge, evaluator, candidate, submission, receipt


def test_public_challenge_verifier_rejects_private_evaluator_leak(tmp_path: Path):
    challenge = tmp_path / "challenge"
    challenge.mkdir()
    (challenge / "challenge.json").write_text('{"challenge_id":"x"}\n', encoding="utf-8")
    files = []
    payload = (challenge / "challenge.json").read_bytes()
    files.append({
        "path": "challenge.json",
        "bytes": len(payload),
        "sha256": sha256(payload).hexdigest(),
    })
    (challenge / CHALLENGE_MANIFEST).write_text(
        json.dumps(
            {
                "schema_version": "scan-reconstruction-challenge-manifest/0.1",
                "engine_version": __version__,
                "files": files,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert verify_public_challenge(challenge)["state"] == "PASS"

    (challenge / "evaluator.json").write_text("{}\n", encoding="utf-8")
    result = verify_public_challenge(challenge)
    assert result["state"] == "FAIL"
    assert any(issue["kind"] == "forbidden_private_artifact" for issue in result["issues"])


def test_worker_receipt_requires_mechanical_network_isolation(tmp_path: Path):
    with tempfile.TemporaryDirectory(dir=tmp_path) as raw:
        td = Path(raw)
        _, challenge, _, candidate, submission, _ = _prepared_trial(td)
        receipt = _worker_receipt(
            td / "bad_receipt.json",
            challenge,
            candidate,
            submission,
            network_during_worker="DECLARED_ONLY",
        )
        result = verify_worker_receipt(challenge, candidate, submission, receipt)
        assert result["state"] == "FAIL"
        assert any(issue["kind"] == "network_isolation_not_enforced" for issue in result["issues"])


def test_worker_receipt_detects_candidate_tamper(tmp_path: Path):
    with tempfile.TemporaryDirectory(dir=tmp_path) as raw:
        td = Path(raw)
        _, challenge, _, candidate, submission, receipt = _prepared_trial(td)
        assert verify_worker_receipt(challenge, candidate, submission, receipt)["state"] == "PASS"
        (candidate / "MainWindow.cpp").write_text("void changed() {}\n", encoding="utf-8")
        result = verify_worker_receipt(challenge, candidate, submission, receipt)
        assert result["state"] == "FAIL"
        assert any(issue["kind"] == "candidate_tree_hash_mismatch" for issue in result["issues"])


def test_end_to_end_independent_reference_worker_proof(tmp_path: Path):
    with tempfile.TemporaryDirectory(dir=tmp_path) as raw:
        td = Path(raw)
        package, challenge, evaluator, candidate, submission, receipt = _prepared_trial(td)

        trial = td / "trial"
        scored = score_reconstruction_trial(
            package,
            evaluator,
            candidate,
            submission,
            trial,
        )
        assert scored["state"] == "PASS"

        proof_path = td / "independent_proof.json"
        proof = verify_independent_reconstruction_proof(
            challenge,
            candidate,
            submission,
            receipt,
            trial,
            output_path=proof_path,
            reference_worker=True,
        )
        assert proof["schema_version"] == "scan-independent-reconstruction-proof/0.1"
        assert proof["state"] == "PASS"
        assert proof["independence"]["state"] == "PASS"
        assert proof["independence"]["repository_checkout"] == "ABSENT"
        assert proof["independence"]["private_evaluator"] == "NOT_PRESENT"
        assert proof["independence"]["network_during_worker"] == "ENFORCED_LINUX_NETWORK_NAMESPACE"
        assert proof["adjudication"]["trial_verification_state"] == "PASS"
        assert proof["adjudication"]["score_state"] == "PASS"
        assert proof["adjudication"]["candidate_self_report_authority"] == "NONE"
        assert proof["claims"]["static_reconstruction_proof"] is True
        assert proof["claims"]["runtime_equivalence_claimed"] is False
        assert proof["claims"]["external_llm_benchmark_claimed"] is False
        assert proof["claims"]["reference_worker"] is True
        assert proof["lineage"]["challenge_manifest_sha256"] == proof["lineage"]["trial_challenge_manifest_sha256"]
        assert json.loads(proof_path.read_text(encoding="utf-8"))["state"] == "PASS"
