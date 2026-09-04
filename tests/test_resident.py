from __future__ import annotations

import json
import os
import subprocess
import sys
from unittest import mock

import pytest

from mantleos.resident import ResidentError, _runner_text, install_resident, remove_resident, resident_status


def local_organs(nest):
    package = nest / "mantle" / "runtime" / "mantleos"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "cli.py").write_text(
        "import json\n"
        "def main(args):\n"
        "    print(json.dumps({'origin': __file__, 'args': args}))\n"
        "    return 0\n", encoding="utf-8"
    )
    return package


def test_resident_requires_explicit_install_and_birth(tmp_path):
    with pytest.raises(ResidentError, match="approve-install"):
        install_resident(tmp_path, approved=False)
    with pytest.raises(Exception, match="No Mantle public delta"):
        install_resident(tmp_path, approved=True)


def test_windows_resident_is_user_level_nest_contained_and_reversible(tmp_path, monkeypatch):
    local_organs(tmp_path)
    monkeypatch.setattr("mantleos.resident.PLATFORM", "nt")
    with (
        mock.patch("mantleos.resident.MantleBody.is_born", new_callable=mock.PropertyMock) as born,
        mock.patch("mantleos.resident.subprocess.run") as run,
    ):
        born.return_value = True
        run.return_value = mock.Mock(returncode=0, stdout="", stderr="")
        receipt = install_resident(tmp_path, approved=True)
        assert receipt["privilege"] == "user-level"
        assert receipt["mechanism"] == "windows-user-logon-task"
        assert receipt["isolated_python"] is True
        assert "-I" in run.call_args.args[0][run.call_args.args[0].index("/TR") + 1]
        registration = tmp_path / ".mantle" / "resident" / "registration.json"
        assert json.loads(registration.read_text(encoding="utf-8"))["nest"] == str(
            tmp_path.resolve()
        )
        assert resident_status(tmp_path)["installed"] is True
        with pytest.raises(ResidentError, match="approve-remove"):
            remove_resident(tmp_path, approved=False)
        assert remove_resident(tmp_path, approved=True)["removed"] is True
        assert not registration.exists()


def test_missing_local_organs_never_registers_or_falls_back(tmp_path):
    (tmp_path / "mantle").mkdir()
    with (
        mock.patch("mantleos.resident.MantleBody.is_born", new_callable=mock.PropertyMock) as born,
        mock.patch("mantleos.resident._run") as run,
    ):
        born.return_value = True
        with pytest.raises(ResidentError, match="NEST-local organs"):
            install_resident(tmp_path, approved=True)
        run.assert_not_called()
        assert not (tmp_path / ".mantle" / "resident").exists()


def test_runner_uses_own_organs_from_unrelated_working_directory(tmp_path):
    nest = (tmp_path / "Body with spaces").resolve()
    package = local_organs(nest)
    foreign = tmp_path / "foreign"
    foreign.mkdir()
    (foreign / "mantleos.py").write_text("raise RuntimeError('wrong runtime')", encoding="utf-8")
    runner = nest / "run-heart.py"
    runner.write_text(_runner_text(nest), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-I", str(runner)], cwd=foreign,
        env={**os.environ, "PYTHONPATH": str(foreign)},
        capture_output=True, text=True, timeout=15, check=True,
    )
    proof = json.loads(result.stdout)
    assert proof["origin"] == str(package / "cli.py")
    assert proof["args"] == ["--nest", str(nest), "watch"]

    (package / "cli.py").unlink()
    result = subprocess.run(
        [sys.executable, "-I", str(runner)], cwd=foreign,
        capture_output=True, text=True, timeout=15, check=False,
    )
    assert result.returncode != 0
    assert "NEST-local organs are missing" in result.stderr


def test_linux_registration_uses_isolated_local_runner(tmp_path, monkeypatch):
    local_organs(tmp_path)
    monkeypatch.setattr("mantleos.resident.PLATFORM", "posix")
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "user-config"))
    with (
        mock.patch("mantleos.resident.MantleBody.is_born", new_callable=mock.PropertyMock) as born,
        mock.patch("mantleos.resident._run") as run,
    ):
        born.return_value = True
        receipt = install_resident(tmp_path, approved=True)
        unit = tmp_path / "user-config" / "systemd" / "user" / (receipt["registration_id"] + ".service")
        assert " -I " in unit.read_text(encoding="utf-8")
        assert receipt["organ_runtime"] == str(tmp_path.resolve() / "mantle" / "runtime")
        assert run.call_args.args[0] == ["systemctl", "--user", "enable", "--now", unit.name]
        assert remove_resident(tmp_path, approved=True)["removed"]
        assert not unit.exists()
