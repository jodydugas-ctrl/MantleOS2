from __future__ import annotations

import json
from pathlib import Path

import pytest

from mantleos.primer import PrimerError, approve_personality, save_personality_candidate


def _construction(root: Path) -> dict:
    (root / "mantle" / "maps").mkdir(parents=True)
    (root / "mantle" / "maps" / "BODY_MAP.json").write_text("{}", encoding="utf-8")
    (root / "mantle" / "ASSIMILATION.json").write_text(
        json.dumps({"declared_purpose": "test"}), encoding="utf-8"
    )
    (root / ".mantle").mkdir()
    prebirth = {"gates": {"primer": "awaiting-developmental-mind"}}
    (root / ".mantle" / "prebirth.json").write_text(json.dumps(prebirth), encoding="utf-8")
    return {"source": "fixture", "body_map": {}, "declared_purpose": "test"}


def test_personality_is_private_and_requires_approval(tmp_path: Path):
    evidence = _construction(tmp_path)
    result = save_personality_candidate(
        tmp_path,
        "# Unique Personality\n\n" + "Observed and bounded behavior. " * 30,
        evidence=evidence,
    )
    candidate = tmp_path / ".mantle" / "construction" / "PERSONALITY.CANDIDATE.md"
    assert candidate.is_file()
    assert not (tmp_path / "mantle" / "primer" / "PERSONALITY.md").exists()
    assert result["status"] == "awaiting-user-approval"
    approved = approve_personality(tmp_path, approved=True)
    assert approved["status"] == "ready-for-birth-review"


def test_personality_rejects_secret_shape(tmp_path: Path):
    evidence = _construction(tmp_path)
    with pytest.raises(PrimerError, match="credential"):
        save_personality_candidate(
            tmp_path,
            "Identity " * 80 + "sk-or-v1-" + "x" * 40,
            evidence=evidence,
        )
