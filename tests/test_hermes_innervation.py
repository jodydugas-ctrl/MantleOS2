from __future__ import annotations

import py_compile
from pathlib import Path

from mantleos.targets.hermes import INSERTIONS, innervate, is_hermes


def _hermes_fixture(root: Path) -> Path:
    agent = root / "agent"
    agent.mkdir()
    (root / "run_agent.py").write_text("class Agent: pass\n", encoding="utf-8")
    (agent / "conversation_loop.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def initialize_conversation(agent):\n"
        "    # Plugin hook: on_session_start — fired once when a brand-new\n"
        "    pass\n",
        encoding="utf-8",
    )
    (agent / "turn_context.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def prepare_turn_context(agent, original_user_message, turn_id):\n"
        "    plugin_user_context = ''\n"
        "    # Gateway must-deliver notes (auto-reset note, first-contact intro,\n"
        "    return plugin_user_context\n",
        encoding="utf-8",
    )
    (agent / "turn_finalizer.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def finalize_turn(agent, final_response, interrupted, original_user_message, turn_id, "
        "completed, failed):\n"
        "    # Plugin hook: post_llm_call\n"
        "    pass\n"
        "    # Plugin hook: on_session_end\n"
        "    return final_response\n",
        encoding="utf-8",
    )
    (agent / "tool_executor.py").write_text(
        "import logging\nlogger=logging.getLogger(__name__)\n"
        "def _emit_terminal_post_tool_call(agent, function_name, function_args, duration_ms=0, "
        "status=None, error_type=None):\n"
        "    try:\n"
        "        pass\n"
        "    except Exception:\n"
        "        pass\n"
        "\n\n"
        "def _cancelled_tool_result(reason: str = \"user interrupt\") -> str:\n"
        "    return reason\n",
        encoding="utf-8",
    )
    return root


def test_direct_innervation_is_reproducible_and_not_a_plugin(tmp_path: Path):
    root = _hermes_fixture(tmp_path)
    assert is_hermes(root)
    records = innervate(root)
    assert len(records) == len(INSERTIONS) == 5
    assert {record["failure_mode"] for record in records} == {"native-no-op"}
    all_source = "\n".join(
        (root / insertion.path).read_text(encoding="utf-8") for insertion in INSERTIONS
    )
    assert "from mantle.nerves import" in all_source
    assert "register_hook" not in all_source
    for path in {root / insertion.path for insertion in INSERTIONS}:
        py_compile.compile(str(path), doraise=True)
