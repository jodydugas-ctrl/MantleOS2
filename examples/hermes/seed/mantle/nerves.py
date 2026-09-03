"""NEST-local direct nerve surface. This is not a plugin."""
try:
    from mantleos.nerves import (
        after_mind,
        authorize_tool,
        before_mind,
        session_ended,
        session_started,
        tool_completed,
        turn_ended,
    )
except Exception:
    def _noop(*args, **kwargs):
        return {"direct": False, "context": "", "message": kwargs.get("user_message", "")}
    after_mind = authorize_tool = before_mind = session_ended = session_started = _noop
    tool_completed = turn_ended = _noop

__all__ = [
    "after_mind", "authorize_tool", "before_mind", "session_ended", "session_started",
    "tool_completed", "turn_ended",
]
