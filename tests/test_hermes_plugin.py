from __future__ import annotations

from mantleos.integrations.hermes import plugin


class FakeContext:
    def __init__(self):
        self.hooks: dict[str, object] = {}

    def register_hook(self, name, callback):
        self.hooks[name] = callback


def test_adapter_registers_only_documented_observation_edges():
    context = FakeContext()
    plugin.register(context)
    assert set(context.hooks) == {
        "on_session_start",
        "pre_llm_call",
        "post_llm_call",
        "post_tool_call",
        "on_session_end",
    }


def test_tool_observation_omits_raw_argument_values(monkeypatch):
    recorded = []
    monkeypatch.setattr(plugin, "_record", lambda kind, data, **kwargs: recorded.append((kind, data)))
    plugin._post_tool(tool_name="terminal", args={"token": "secret-value"}, status="ok", duration_ms=3)
    kind, data = recorded[0]
    assert kind == "hermes.tool.completed"
    assert data["argument_keys"] == ["token"]
    assert "secret-value" not in repr(data)

