"""Fail-closed audit for material that must never enter a public delta."""

from __future__ import annotations

import argparse
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

FORBIDDEN_PARTS = {".mantle", "COMMUNICATION.TXT", "Food.txt"}
FORBIDDEN_SUFFIXES = {".key", ".pem", ".p12", ".pfx"}
SKIP_PARTS = {
    ".artifacts",
    ".assimilation-work",
    ".git",
    ".pytest-tmp",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "venv",
}
SECRET_PATTERNS = {
    "OpenRouter API key": re.compile(rb"sk-or-v1-[A-Za-z0-9_-]{20,}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9]{20,}"),
}


@dataclass(frozen=True)
class Finding:
    path: str
    reason: str


def _files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file() and not (set(path.relative_to(root).parts) & SKIP_PARTS):
            yield path


def audit_public_tree(root: Path) -> list[Finding]:
    root = root.resolve()
    findings: list[Finding] = []
    for path in _files(root):
        relative = path.relative_to(root)
        if any(part in FORBIDDEN_PARTS for part in relative.parts):
            findings.append(Finding(relative.as_posix(), "private organism path"))
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(Finding(relative.as_posix(), "private-key file type"))
            continue
        try:
            data = path.read_bytes()
        except OSError:
            findings.append(Finding(relative.as_posix(), "unreadable file"))
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(data):
                findings.append(Finding(relative.as_posix(), label))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a tree for non-public Mantle material")
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    findings = audit_public_tree(Path(args.root))
    if findings:
        for finding in findings:
            print(f"REFUSED {finding.path}: {finding.reason}")
        return 1
    print("Public-tree audit passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
