"""Opt-in Hermes adapter. It observes; it never replaces native Hermes behavior."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import suppress
from pathlib import Path
from typing import Any


def _mantle_config() -> dict[str, Any]:
    """Read user-facing behavior from Hermes config; env is an internal bridge only."""
    try:
        from hermes_cli.config import cfg_get, load_config

        config = load_config()
        section = cfg_get(config, "mantle")
        return section if isinstance(section, dict) else {}
    except Exception:
        return {}


def _direct_route() -> bool:
    configured = _mantle_config().get("appai_route")
    if configured is not None:
        return bool(configured)
    return os.environ.get("MANTLE_APPAI_ROUTE", "").strip().lower() in {"1", "true", "yes", "on"}


def _body():
    try:
        from mantleos.runtime import MantleBody

        configured_nest = _mantle_config().get("nest")
        nest = Path(configured_nest or os.environ.get("MANTLE_NEST", Path.cwd()))
        body = MantleBody(nest)
        return body if body.is_born else None
    except Exception:
        return None


def _record(kind: str, data: dict[str, Any], *, layer: str = "layer-0") -> None:
    body = _body()
    if body is not None:
        body.record_observation(layer, kind, data)


def _session_start(session_id: str = "", model: str = "", platform: str = "", **_: Any) -> None:
    body = _body()
    if body is not None:
        body.recover_host_heartbeats()
    _record("hermes.session.started", {"session_id": session_id, "model": model, "platform": platform})


def _pre_llm(
    user_message: str = "", session_id: str = "", turn_id: str = "", platform: str = "", **_: Any
):
    direct = _direct_route()
    if not direct:
        _record("hermes.user.turn", {"session_id": session_id, "platform": platform, "message": user_message})
        return None
    body = _body()
    if body is None:
        return None
    _record(
        "appai.direct-user-message",
        {"session_id": session_id, "platform": platform, "message": user_message},
        layer="communication",
    )
    beat = body.begin_host_heartbeat(session_id, turn_id)
    continuity = body.prepare_mind_update(session_id, turn_id)
    return {
        "context": (
            "MantleOS continuity: this is an explicitly routed AppAI turn. "
            f"Unscheduled Heartbeat {beat['heartbeat_id']} is active. "
            "Treat the dedicated profile's SOUL.md as the sealed Primer projection; "
            "do not reinterpret ordinary Hermes activity as AppAI MIND activity.\n"
            "Unacknowledged Body history follows; it is bounded and advances only "
            "after a successful response:\n"
            + json.dumps(continuity["events"], sort_keys=True, ensure_ascii=False)
        )
    }


def _post_llm(
    user_message: str = "",
    assistant_response: str = "",
    session_id: str = "",
    turn_id: str = "",
    platform: str = "",
    **_: Any,
) -> None:
    direct = _direct_route()
    _record(
        "appai.mind.turn" if direct else "hermes.native-llm.turn",
        {
            "session_id": session_id,
            "platform": platform,
            "user_message": user_message,
            "assistant_response": assistant_response,
        },
        layer="communication" if direct else "layer-0",
    )
    if direct:
        body = _body()
        if body is not None:
            body.acknowledge_mind_update(session_id, turn_id)
            body.complete_host_heartbeat(session_id, turn_id, mind_status="responded")


def _post_tool(
    tool_name: str = "", args: dict[str, Any] | None = None, status: str = "", duration_ms: int = 0, **_: Any
) -> None:
    # Raw results and argument values may contain secrets. Preserve the action,
    # argument shape, and a stable digest without copying those values into
    # append-only memory. Tool-specific adapters may later add reviewed fields.
    arguments = args or {}
    digest = hashlib.sha256(
        json.dumps(arguments, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    _record(
        "hermes.tool.completed",
        {
            "tool": tool_name,
            "argument_keys": sorted(str(key) for key in arguments),
            "arguments_sha256": digest,
            "status": status,
            "duration_ms": duration_ms,
        },
    )


def _session_end(
    session_id: str = "",
    turn_id: str = "",
    completed: bool = False,
    failed: bool = False,
    interrupted: bool = False,
    **_: Any,
) -> None:
    _record(
        "hermes.session.ended",
        {"session_id": session_id, "completed": completed, "failed": failed, "interrupted": interrupted},
    )
    direct = _direct_route()
    if direct:
        body = _body()
        if body is not None:
            state = "responded" if completed and not failed and not interrupted else "unavailable"
            with suppress(Exception):
                body.complete_host_heartbeat(session_id, turn_id, mind_status=state)


def register(ctx) -> None:
    ctx.register_hook("on_session_start", _session_start)
    ctx.register_hook("pre_llm_call", _pre_llm)
    ctx.register_hook("post_llm_call", _post_llm)
    ctx.register_hook("post_tool_call", _post_tool)
    ctx.register_hook("on_session_end", _session_end)
