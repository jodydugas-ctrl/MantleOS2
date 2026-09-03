from __future__ import annotations

from mantleos import nerves


def test_unborn_or_absent_body_is_native_noop(monkeypatch, tmp_path):
    monkeypatch.setenv("MANTLE_NEST", str(tmp_path))
    result = nerves.before_mind(
        user_message="ordinary Hermes turn",
        session_id="s",
        turn_id="t",
        surface="cli",
    )
    assert result == {"direct": False, "context": "", "message": "ordinary Hermes turn"}


def test_explicit_route_is_not_inferred_from_agentic_body():
    assert nerves._direct_message("hello") == (False, "hello")
    assert nerves._direct_message("/mantle hello") == (True, "hello")
