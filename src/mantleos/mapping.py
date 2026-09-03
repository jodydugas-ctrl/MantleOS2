"""Static Body mapping for repository and directory NESTs.

Mapping is intentionally non-executing.  It describes what is present and
where candidate nerves may attach; it never claims that a discovered seam is
safe until the corresponding behavior gate has been exercised.
"""

from __future__ import annotations

import hashlib
import os
from collections import Counter
from pathlib import Path

from .contracts import BodyMap, CapabilitySpec, contract_dict

IGNORED_PARTS = {".git", ".mantle", ".venv", "venv", "node_modules", "__pycache__"}
LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".rs": "rust",
    ".go": "go",
    ".cs": "csharp",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".html": "html",
    ".css": "css",
    ".sh": "shell",
    ".ps1": "powershell",
}
ENTRYPOINT_NAMES = {
    "main.py",
    "__main__.py",
    "cli.py",
    "app.py",
    "server.py",
    "index.js",
    "index.ts",
    "main.js",
    "main.ts",
    "index.html",
}
BUILD_MARKERS = {
    "pyproject.toml": "python-pyproject",
    "setup.py": "python-setuptools",
    "requirements.txt": "python-requirements",
    "package.json": "node-package",
    "Cargo.toml": "cargo",
    "go.mod": "go-modules",
    "pom.xml": "maven",
    "build.gradle": "gradle",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
}


def iter_body_files(root: Path):
    for current, directories, filenames in os.walk(root):
        directories[:] = sorted(name for name in directories if name not in IGNORED_PARTS)
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                continue
            yield path


def map_body(root: Path, *, source_uri: str, source_fingerprint: str) -> dict:
    root = root.resolve()
    languages: Counter[str] = Counter()
    entrypoints: list[str] = []
    build_systems: set[str] = set()
    behavior: set[str] = set()
    capabilities: list[CapabilitySpec] = []

    relative_paths: set[str] = set()
    for path in iter_body_files(root):
        relative = path.relative_to(root).as_posix()
        relative_paths.add(relative)
        language = LANGUAGES.get(path.suffix.lower())
        if language:
            languages[language] += 1
        if path.name in ENTRYPOINT_NAMES:
            entrypoints.append(relative)
        marker = BUILD_MARKERS.get(path.name)
        if marker:
            build_systems.add(marker)

    if "cli.py" in relative_paths or "hermes_cli/main.py" in relative_paths:
        behavior.add("terminal-conversation")
    if any(path.startswith("gateway/") for path in relative_paths):
        behavior.add("gateway-conversation")
    if any("tool" in Path(path).parts or "tools" in Path(path).parts for path in relative_paths):
        behavior.add("tool-execution")
    if any(path.endswith(("index.html", ".tsx")) for path in relative_paths):
        behavior.add("graphical-interface")

    hermes_markers = {"run_agent.py", "agent/conversation_loop.py", "agent/turn_context.py"}
    if hermes_markers.issubset(relative_paths):
        capabilities.extend(
            [
                CapabilitySpec(
                    "hermes.conversation",
                    "agent.conversation_loop.run_conversation",
                    "Run a native Hermes conversation turn",
                    "communicate",
                    "mantle.hermes-conversation-input.v2",
                    "native-turn-receipt",
                ),
                CapabilitySpec(
                    "hermes.tool-dispatch",
                    "agent.tool_executor",
                    "Dispatch a registered Hermes tool",
                    "external-effect",
                    "mantle.hermes-tool-input.v2",
                    "native-tool-result",
                ),
            ]
        )

    unknowns: list[str] = []
    if not languages:
        unknowns.append("No supported source language was identified")
    if not entrypoints:
        unknowns.append("No known application entrypoint was identified")

    mapped = BodyMap(
        source_uri=source_uri,
        source_fingerprint=source_fingerprint,
        languages=dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        entrypoints=tuple(sorted(entrypoints)),
        build_systems=tuple(sorted(build_systems)),
        behavior_surfaces=tuple(sorted(behavior)),
        capabilities=tuple(capabilities),
        unknowns=tuple(unknowns),
    )
    result = contract_dict(mapped)
    result["map_sha256"] = hashlib.sha256(
        repr(sorted(result.items())).encode("utf-8")
    ).hexdigest()
    return result
