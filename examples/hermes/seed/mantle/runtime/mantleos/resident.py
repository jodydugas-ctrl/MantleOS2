"""Explicit user-level registration for a NEST-contained resident Heart."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

from .runtime import MantleBody, MantleError, _atomic_write, utc_now

PLATFORM = os.name


class ResidentError(MantleError):
    pass


def _registration_id(nest: Path) -> str:
    suffix = hashlib.sha256(str(nest).casefold().encode("utf-8")).hexdigest()[:12]
    return f"MantleOS2-{suffix}"


def _paths(nest: Path) -> tuple[Path, Path]:
    root = nest / ".mantle" / "resident"
    return root / "registration.json", root / "run-heart.py"


def _runner_text(nest: Path) -> str:
    return (
        "from mantleos.cli import main\n\n"
        f"raise SystemExit(main(['--nest', {str(nest)!r}, 'watch']))\n"
    )


def _run(arguments: list[str]) -> None:
    try:
        subprocess.run(arguments, check=True, capture_output=True, text=True)
    except (FileNotFoundError, subprocess.CalledProcessError) as exc:
        detail = getattr(exc, "stderr", None) or getattr(exc, "stdout", None) or str(exc)
        raise ResidentError(str(detail).strip()) from None


def install_resident(nest: str | Path, *, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ResidentError("Resident Heart installation requires --approve-install")
    nest = Path(nest).resolve()
    if not MantleBody(nest).is_born:
        raise ResidentError("A resident Heart can be installed only after birth")
    registration_path, runner = _paths(nest)
    registration_id = _registration_id(nest)
    _atomic_write(runner, _runner_text(nest).encode("utf-8"))

    if PLATFORM == "nt":
        command = subprocess.list2cmdline([sys.executable, str(runner)])
        _run(
            [
                "schtasks.exe",
                "/Create",
                "/TN",
                registration_id,
                "/SC",
                "ONLOGON",
                "/TR",
                command,
                "/RL",
                "LIMITED",
                "/F",
            ]
        )
        mechanism = "windows-user-logon-task"
        external = registration_id
    else:
        config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        unit = config_root / "systemd" / "user" / f"{registration_id}.service"
        unit.parent.mkdir(parents=True, exist_ok=True)
        quoted_python = shlex.quote(sys.executable)
        quoted_runner = shlex.quote(str(runner))
        unit_text = (
            "[Unit]\nDescription=MantleOS 2 resident Heart\n\n"
            "[Service]\nType=simple\n"
            f"ExecStart={quoted_python} {quoted_runner}\nRestart=on-failure\n\n"
            "[Install]\nWantedBy=default.target\n"
        )
        _atomic_write(unit, unit_text.encode("utf-8"))
        _run(["systemctl", "--user", "daemon-reload"])
        _run(["systemctl", "--user", "enable", "--now", unit.name])
        mechanism = "systemd-user-service"
        external = str(unit)

    receipt = {
        "schema": "mantle.resident-heart.v2",
        "registration_id": registration_id,
        "mechanism": mechanism,
        "external_registration": external,
        "runner": str(runner),
        "nest": str(nest),
        "installed_at": utc_now(),
        "authority": "explicit-user-approval",
        "privilege": "user-level",
    }
    _atomic_write(
        registration_path,
        (json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
    )
    return receipt


def resident_status(nest: str | Path) -> dict[str, Any]:
    nest = Path(nest).resolve()
    registration_path, runner = _paths(nest)
    if not registration_path.is_file():
        return {"installed": False, "nest": str(nest)}
    try:
        receipt = json.loads(registration_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ResidentError("Resident Heart receipt is unreadable") from exc
    return {"installed": runner.is_file(), **receipt}


def remove_resident(nest: str | Path, *, approved: bool) -> dict[str, Any]:
    if not approved:
        raise ResidentError("Resident Heart removal requires --approve-remove")
    nest = Path(nest).resolve()
    receipt = resident_status(nest)
    if not receipt.get("installed"):
        return {"removed": False, "reason": "not-installed", "nest": str(nest)}
    if receipt["mechanism"] == "windows-user-logon-task":
        _run(["schtasks.exe", "/Delete", "/TN", receipt["registration_id"], "/F"])
    else:
        unit = Path(receipt["external_registration"])
        _run(["systemctl", "--user", "disable", "--now", unit.name])
        if unit.is_file():
            unit.unlink()
        _run(["systemctl", "--user", "daemon-reload"])
    registration_path, runner = _paths(nest)
    if runner.is_file():
        runner.unlink()
    if registration_path.is_file():
        registration_path.unlink()
    return {"removed": True, "registration_id": receipt["registration_id"], "nest": str(nest)}
