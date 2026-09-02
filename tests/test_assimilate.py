from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from mantleos.assimilate import (
    AssimilationError,
    census_repository,
    construct_nest,
    normalize_github_source,
)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()


def _host(tmp_path: Path) -> Path:
    root = tmp_path / "host"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "Mantle Test")
    _git(root, "config", "user.email", "mantle@example.invalid")
    (root / "LICENSE").write_text("MIT test fixture\n", encoding="utf-8")
    (root / "app.py").write_text("print('native body')\n", encoding="utf-8")
    _git(root, "add", "LICENSE", "app.py")
    _git(root, "commit", "-m", "host fixture")
    return root


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("github.com/nousresearch/hermes-agent", "https://github.com/nousresearch/hermes-agent"),
        ("https://github.com/NousResearch/hermes-agent.git", "https://github.com/NousResearch/hermes-agent"),
        ("git@github.com:nousresearch/hermes-agent.git", "https://github.com/nousresearch/hermes-agent"),
    ],
)
def test_normalize_github_source(source: str, expected: str):
    assert normalize_github_source(source) == (expected, "hermes-agent")


def test_non_github_source_is_refused():
    with pytest.raises(AssimilationError):
        normalize_github_source("https://example.com/owner/repo")


def test_read_only_census_is_stable(tmp_path: Path):
    root = _host(tmp_path)
    before = census_repository(root)
    after = census_repository(root)
    assert before == after
    assert before.file_count == 2
    assert before.source_fingerprint.startswith("sha256:")


def test_constructs_unborn_delta_without_executing_host(tmp_path: Path):
    root = _host(tmp_path)
    sentinel = root / "would-run.txt"
    (root / "setup.py").write_text(
        "from pathlib import Path\nPath('would-run.txt').write_text('bad')\n",
        encoding="utf-8",
    )
    _git(root, "add", "setup.py")
    _git(root, "commit", "-m", "untrusted candidate")

    manifest = construct_nest(
        root,
        source_url="https://github.com/example/host",
        command="mantle assimilate github.com/example/host",
    )

    assert manifest["status"] == "constructed-not-born"
    assert manifest["default_body"]["logical_layer"] == 0
    assert manifest["activation"]["automatic"] is False
    assert not sentinel.exists()
    assert not (root / "COMMUNICATION.TXT").exists()
    assert not (root / ".mantle" / "keys").exists()
    assert (root / "mantle" / "ASSIMILATION.json").is_file()
    assert (root / ".mantle" / "prebirth.json").is_file()
    assert "/.mantle/" in (root / ".gitignore").read_text(encoding="utf-8")

    public = json.loads((root / "mantle" / "ASSIMILATION.json").read_text(encoding="utf-8"))
    assert public["source"]["commit"] == _git(root, "rev-parse", "HEAD")
    assert public["gates"]["birth"] == "not-authorized"


def test_existing_mantle_tissue_is_not_overwritten(tmp_path: Path):
    root = _host(tmp_path)
    (root / "mantle").mkdir()
    with pytest.raises(AssimilationError, match="already contains"):
        construct_nest(root, source_url="https://github.com/example/host", command="test")

