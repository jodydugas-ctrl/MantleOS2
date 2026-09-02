from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_workflows_are_valid_yaml():
    workflows = sorted((ROOT / ".github" / "workflows").glob("*.yml"))
    assert workflows
    for workflow in workflows:
        parsed = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), workflow
        assert "jobs" in parsed, workflow


def test_hermes_lock_is_an_exact_commit():
    lock = json.loads((ROOT / "examples" / "hermes" / "upstream.lock.json").read_text(encoding="utf-8"))
    commit = lock["commit"]
    assert len(commit) == 40
    assert all(character in "0123456789abcdef" for character in commit)

