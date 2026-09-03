"""NEST-local direct nerve surface. This is not a plugin."""
try:
    from mantleos.nerves import after_mind, before_mind, session_ended, session_started, tool_completed
except Exception:
    def _noop(*args, **kwargs):
        return {"direct": False, "context": "", "message": kwargs.get("user_message", "")}
    after_mind = before_mind = session_ended = session_started = tool_completed = _noop

__all__ = ["after_mind", "before_mind", "session_ended", "session_started", "tool_completed"]
