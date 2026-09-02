from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout.rstrip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a constructed Hermes delta")
    parser.add_argument("nest", type=Path)
    parser.add_argument("--expected-commit")
    args = parser.parse_args()
    nest = args.nest.resolve()
    manifest_path = nest / "mantle" / "ASSIMILATION.json"
    if not manifest_path.is_file():
        raise SystemExit("missing mantle/ASSIMILATION.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual = git(nest, "rev-parse", "HEAD")
    if manifest["source"]["commit"] != actual:
        raise SystemExit("manifest commit does not match the NEST")
    if args.expected_commit and actual != args.expected_commit:
        raise SystemExit("NEST does not match the certified upstream commit")
    if manifest["status"] != "constructed-not-born":
        raise SystemExit("reference delta must remain un-born")
    if (nest / "COMMUNICATION.TXT").exists() or (nest / ".mantle" / "keys").exists():
        raise SystemExit("construction created live organism material")

    changed = []
    for line in git(nest, "status", "--short").splitlines():
        path = line[3:].replace("\\", "/")
        changed.append(path)
        if path != ".gitignore" and not path.startswith("mantle/"):
            raise SystemExit(f"unexpected host change: {path}")
    if ".gitignore" not in changed or not any(path.startswith("mantle/") for path in changed):
        raise SystemExit("expected delta surfaces are missing")
    print(json.dumps({"ok": True, "commit": actual, "changed_paths": changed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
