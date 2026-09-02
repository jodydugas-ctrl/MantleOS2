"""Read-first GitHub NEST assimilation for MantleOS 2.

The constructor clones and inventories a host, then writes only Mantle-owned
construction tissue.  It never executes code from the cloned repository and
never performs birth.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .constitution import species_kernel_markdown

SCHEMA = "mantle.assimilation.v2"
GITHUB_REPOSITORY = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PRIVATE_NAMES = {".git", ".mantle", "__pycache__", ".pytest_cache", ".venv", "venv"}
GITIGNORE_BLOCK = """# MantleOS private organism state and local communication surfaces.
/.mantle/
/COMMUNICATION.TXT
/Food.txt
"""


class AssimilationError(RuntimeError):
    """A construction or evidence gate could not be satisfied."""


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_github_source(source: str) -> tuple[str, str]:
    """Return canonical HTTPS URL and repository name for a GitHub source."""
    raw = source.strip().rstrip("/")
    if raw.startswith("git@github.com:"):
        raw = raw.removeprefix("git@github.com:")
    elif raw.startswith("github.com/"):
        raw = raw.removeprefix("github.com/")
    elif raw.startswith("https://github.com/") or raw.startswith("http://github.com/"):
        parsed = urlparse(raw)
        raw = parsed.path.strip("/")
    else:
        raise AssimilationError("The alpha constructor accepts only github.com repositories")
    raw = raw.removesuffix(".git")
    if not GITHUB_REPOSITORY.fullmatch(raw):
        raise AssimilationError("GitHub source must identify exactly one owner/repository")
    owner, repository = raw.split("/", 1)
    return f"https://github.com/{owner}/{repository}", repository


def _git(arguments: Iterable[str], *, cwd: Path | None = None) -> str:
    command = ["git", *arguments]
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        raise AssimilationError("Git is required for GitHub assimilation") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "git operation failed").strip().splitlines()[-1]
        raise AssimilationError(detail) from None
    return completed.stdout.strip()


@dataclass(frozen=True)
class RepositoryCensus:
    file_count: int
    byte_count: int
    source_fingerprint: str
    extensions: dict[str, int]
    sample: list[str]


def _host_files(root: Path) -> Iterable[Path]:
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(item for item in directories if item not in PRIVATE_NAMES)
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                continue
            yield path


def census_repository(root: Path) -> RepositoryCensus:
    """Fingerprint a host tree without interpreting or executing its contents."""
    root = root.resolve()
    aggregate = hashlib.sha256()
    extensions: dict[str, int] = {}
    byte_count = 0
    sample: list[str] = []
    count = 0
    for path in _host_files(root):
        relative = path.relative_to(root).as_posix()
        size = path.stat().st_size
        digest = sha256_file(path)
        aggregate.update(relative.encode("utf-8"))
        aggregate.update(b"\0")
        aggregate.update(str(size).encode("ascii"))
        aggregate.update(b"\0")
        aggregate.update(digest.encode("ascii"))
        aggregate.update(b"\n")
        suffix = path.suffix.lower() or "[none]"
        extensions[suffix] = extensions.get(suffix, 0) + 1
        byte_count += size
        count += 1
        if len(sample) < 100:
            sample.append(relative)
    return RepositoryCensus(
        file_count=count,
        byte_count=byte_count,
        source_fingerprint=f"sha256:{aggregate.hexdigest()}",
        extensions=dict(sorted(extensions.items(), key=lambda item: (-item[1], item[0]))),
        sample=sample,
    )


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _append_gitignore(nest: Path) -> dict[str, str]:
    path = nest / ".gitignore"
    before = sha256_file(path) if path.exists() else hashlib.sha256(b"").hexdigest()
    existing = path.read_text(encoding="utf-8") if path.exists() else ""
    if GITIGNORE_BLOCK not in existing:
        separator = (
            ""
            if not existing or existing.endswith("\n\n")
            else ("\n" if existing.endswith("\n") else "\n\n")
        )
        _atomic_text(path, existing + separator + GITIGNORE_BLOCK)
    return {"path": ".gitignore", "before_sha256": before, "after_sha256": sha256_file(path)}


def _template_text(name: str) -> str:
    return files("mantleos.templates.hermes").joinpath(name).read_text(encoding="utf-8")


def _hermes_integration_text(name: str) -> str:
    return files("mantleos.integrations.hermes").joinpath(name).read_text(encoding="utf-8")


def _write_public_delta(nest: Path, manifest: dict[str, Any]) -> list[str]:
    public = nest / "mantle"
    payloads = {
        "__init__.py": (
            '"""MantleOS 2 NEST controls. Requires the mantleos2 package."""\n'
            "from mantleos.runtime import Book, MantleBody, MantleError, VCW\n"
            '__all__ = ["Book", "MantleBody", "MantleError", "VCW"]\n'
        ),
        "__main__.py": "from mantleos.cli import main\nraise SystemExit(main())\n",
        "README.md": _template_text("README.md"),
        "primer/COMMANDMENTS.md": species_kernel_markdown(),
        "primer/PERSONALITY.md": _template_text("PERSONALITY.md"),
        "hermes_plugin/__init__.py": _hermes_integration_text("plugin.py"),
        "hermes_plugin/plugin.yaml": _hermes_integration_text("plugin.yaml"),
    }
    written: list[str] = []
    for relative, value in payloads.items():
        target = public / relative
        if target.exists():
            raise AssimilationError(f"Refusing to overwrite existing candidate tissue: {target}")
        _atomic_text(target, value)
        written.append(target.relative_to(nest).as_posix())
    _atomic_text(public / "ASSIMILATION.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
    written.append("mantle/ASSIMILATION.json")
    return sorted(written)


def construct_nest(
    nest: Path,
    *,
    source_url: str,
    command: str,
    identity_suggestion: str = "The Compiler",
) -> dict[str, Any]:
    """Construct an un-born Mantle delta in an already-cloned Git NEST."""
    nest = nest.resolve()
    if not (nest / ".git").is_dir():
        raise AssimilationError("The NEST must be a Git checkout")
    if (nest / "mantle").exists() or (nest / ".mantle").exists():
        raise AssimilationError("The NEST already contains Mantle construction tissue")

    commit = _git(["rev-parse", "HEAD"], cwd=nest)
    tree = _git(["rev-parse", "HEAD^{tree}"], cwd=nest)
    branch = _git(["branch", "--show-current"], cwd=nest) or None
    before = census_repository(nest)
    license_path = next(
        (
            path
            for name in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")
            if (path := nest / name).is_file()
        ),
        None,
    )
    host_edge = _append_gitignore(nest)
    manifest: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "constructed-not-born",
        "constructed_at": utc_now(),
        "source": {
            "canonical_url": source_url,
            "branch": branch,
            "commit": commit,
            "tree": tree,
            "license": {
                "path": license_path.name if license_path else None,
                "sha256": sha256_file(license_path) if license_path else None,
                "evidence": "observed" if license_path else "unknown",
            },
            "census": asdict(before),
        },
        "default_body": {
            "logical_layer": 0,
            "name": "Default Body",
            "substrate": "native-nest",
            "self_boundary": "The NEST is Layer 0 substrate and remains OTHER; it is not SELF.",
            "compatibility_rule": "The host must retain ordinary behavior without the AppAI MIND.",
        },
        "identity_suggestion": identity_suggestion,
        "primer_candidate": {
            "status": "ready-for-birth-review",
            "commandments": "primer/COMMANDMENTS.md",
            "personality": "primer/PERSONALITY.md",
            "developmental_mind": "external construction process; not the organism MIND",
            "provenance": [
                "shared AppAI species kernel",
                "frame-preserving Cuttlefish persona distillation",
                "Hermes source and development contract",
                "operator clarification and review",
            ],
        },
        "host_edges": [host_edge],
        "activation": {
            "automatic": False,
            "birth_requires_separate_approval": True,
            "hermes_plugin_requires_opt_in": True,
        },
        "gates": {
            "source_identified": "verified",
            "read_only_census": "verified",
            "host_behavior": "requires-runtime-verification",
            "primer": "ready-for-birth-review",
            "birth": "not-authorized",
        },
    }
    delta_paths = _write_public_delta(nest, manifest)
    manifest["delta"] = {
        "paths": delta_paths,
        "sha256": {
            path: sha256_file(nest / path)
            for path in delta_paths
            if path != "mantle/ASSIMILATION.json"
        },
    }
    _atomic_text(
        nest / "mantle" / "ASSIMILATION.json",
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    )

    prebirth = {
        "schema": "mantle.prebirth.v2",
        "status": "constructed-not-born",
        "command": command,
        "source": manifest["source"],
        "public_delta": "mantle/",
        "default_body": "Layer 0 / NEST",
        "identity_suggestion": identity_suggestion,
        "approvals": {"assimilation_construction": True, "foreign_code_execution": False, "birth": False},
        "gates": {
            "source_identified": "verified",
            "read_only_census": "verified",
            "host_behavior": "requires-runtime-verification",
            "primer": "ready-for-birth-review",
            "birth": "not-authorized",
        },
        "constraints": [
            "Host-native behavior remains available without a MIND.",
            "No live VCW, identity key, or communication file exists before birth.",
            "The Hermes adapter is opt-in and uses documented host edges.",
        ],
    }
    _atomic_text(
        nest / ".mantle" / "prebirth.json",
        json.dumps(prebirth, indent=2, ensure_ascii=False) + "\n",
    )
    return manifest


def assimilate_github(
    source: str,
    *,
    destination: str | Path | None = None,
    ref: str | None = None,
) -> dict[str, Any]:
    canonical_url, repository = normalize_github_source(source)
    target = Path(destination or repository).resolve()
    if target.exists() and any(target.iterdir()):
        raise AssimilationError(f"Destination is not empty: {target}")
    if target.exists() and not target.is_dir():
        raise AssimilationError(f"Destination is not a directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="mantle-git-hooks-") as hook_dir:
        clone = [
            "-c",
            f"core.hooksPath={hook_dir}",
            "-c",
            "filter.lfs.smudge=",
            "-c",
            "filter.lfs.required=false",
            "clone",
            "--no-recurse-submodules",
        ]
        clone.extend([canonical_url, str(target)])
        _git(clone)
    if ref:
        _git(["fetch", "--depth", "1", "origin", ref], cwd=target)
        _git(["checkout", "--detach", "FETCH_HEAD"], cwd=target)

    command = f"mantle assimilate {source}"
    if ref:
        command += f" --ref {ref}"
    if destination:
        command += f" --destination {destination}"
    return construct_nest(target, source_url=canonical_url, command=command)
