from __future__ import annotations

from mantleos.contracts import (
    ActionFrame,
    BodyMap,
    Direction,
    NerveSpec,
    SourceAnchor,
    contract_dict,
)


def test_contracts_are_substrate_neutral_and_json_ready():
    mapped = BodyMap(
        source_uri="fixture://body",
        source_fingerprint="sha256:" + "0" * 64,
        languages={"javascript": 2},
        entrypoints=("index.html",),
    )
    result = contract_dict(mapped)
    assert result["default_body"] == "NEST"
    assert result["logical_layer"] == 0
    assert result["languages"] == {"javascript": 2}


def test_nerve_and_action_are_distinct_contracts():
    nerve = NerveSpec(
        nerve_id="fixture:save",
        direction=Direction.BIDIRECTIONAL,
        semantic_event="document.saved",
        anchor=SourceAnchor("app.js", "save", "0" * 64, "after-statement"),
        capability_id="document.save",
    )
    action = ActionFrame("a1", "document.save", {"path": "note.txt"}, "thought:1")
    assert contract_dict(nerve)["direction"] == "bidirectional"
    assert contract_dict(action)["requested_by"] == "MIND"
