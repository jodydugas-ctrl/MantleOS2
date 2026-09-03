from __future__ import annotations

import json
from unittest import mock

import pytest

from mantleos.resident import ResidentError, install_resident, remove_resident, resident_status


def test_resident_requires_explicit_install_and_birth(tmp_path):
    with pytest.raises(ResidentError, match="approve-install"):
        install_resident(tmp_path, approved=False)
    with pytest.raises(Exception, match="No Mantle public delta"):
        install_resident(tmp_path, approved=True)


def test_windows_resident_is_user_level_nest_contained_and_reversible(tmp_path, monkeypatch):
    mantle = tmp_path / "mantle"
    mantle.mkdir()
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
        registration = tmp_path / ".mantle" / "resident" / "registration.json"
        assert json.loads(registration.read_text(encoding="utf-8"))["nest"] == str(
            tmp_path.resolve()
        )
        assert resident_status(tmp_path)["installed"] is True
        with pytest.raises(ResidentError, match="approve-remove"):
            remove_resident(tmp_path, approved=False)
        assert remove_resident(tmp_path, approved=True)["removed"] is True
        assert not registration.exists()
