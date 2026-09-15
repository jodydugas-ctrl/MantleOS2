from __future__ import annotations

import os
from pathlib import Path
import shutil

import pytest

from scan.adapters.typescript_electron_precise import TypeScriptElectronAdapter
from scan.inventory import record_from_bytes
from scan.model import Edge, Evidence, ExtractionResult, Node, stable_id


def test_repeated_call_sites_do_not_merge_channels(tmp_path: Path):
    adapter = TypeScriptElectronAdapter()
    data = b"first();\nsecond();\n"
    rec = record_from_bytes("sample.ts", data)

    old = stable_id("call_reference", rec.id, "ipcRenderer.invoke")
    ev1 = Evidence("EV1", rec.id, rec.path, 1, 1, "MEASURED", "test", "first")
    ev2 = Evidence("EV2", rec.id, rec.path, 2, 2, "MEASURED", "test", "second")
    fn1 = Node("FN1", "symbol", "first", rec.id, rec.path, "MAPPED", {}, ["EV1"])
    fn2 = Node("FN2", "symbol", "second", rec.id, rec.path, "MAPPED", {}, ["EV2"])
    call1 = Node(old, "call_reference", "ipcRenderer.invoke", rec.id, rec.path, "PARTIAL",
                 {"callee": "ipcRenderer.invoke", "arguments": ["IPC.first"]}, ["EV1"])
    call2 = Node(old, "call_reference", "ipcRenderer.invoke", rec.id, rec.path, "PARTIAL",
                 {"callee": "ipcRenderer.invoke", "arguments": ["IPC.second"]}, ["EV2"])
    ch1 = Node("CH1", "ipc_channel", "first", rec.id, rec.path, "MAPPED", {}, ["EV1"])
    ch2 = Node("CH2", "ipc_channel", "second", rec.id, rec.path, "MAPPED", {}, ["EV2"])
    result = ExtractionResult(
        nodes=[fn1, fn2, call1, call2, ch1, ch2],
        edges=[
            Edge("E1", "FN1", old, "calls", "MAPPED", {}, ["EV1"]),
            Edge("E2", old, "CH1", "crosses_boundary", "MAPPED", {}, ["EV1"]),
            Edge("E3", "FN2", old, "calls", "MAPPED", {}, ["EV2"]),
            Edge("E4", old, "CH2", "crosses_boundary", "MAPPED", {}, ["EV2"]),
        ],
        evidence=[ev1, ev2],
    )

    out = adapter._preserve_callsite_identity(rec, result)
    calls = [n for n in out.nodes if n.kind == "call_reference"]
    assert len(calls) == 2
    assert len({n.id for n in calls}) == 2

    calls_from_first = [e.dst for e in out.edges if e.src == "FN1" and e.kind == "calls"]
    calls_from_second = [e.dst for e in out.edges if e.src == "FN2" and e.kind == "calls"]
    assert len(calls_from_first) == 1
    assert len(calls_from_second) == 1
    assert calls_from_first[0] != calls_from_second[0]

    assert {(e.src, e.dst) for e in out.edges if e.kind == "crosses_boundary"} == {
        (calls_from_first[0], "CH1"),
        (calls_from_second[0], "CH2"),
    }


@pytest.mark.skipif(
    not (shutil.which("node") and os.environ.get("SCAN_TYPESCRIPT_MODULE")),
    reason="scanner-owned TypeScript parser is not installed in this environment",
)
def test_react_wrappers_keep_component_and_hook_assigned_identity(tmp_path: Path):
    source = r'''
import { memo, useCallback } from 'react'

const Child = memo(function Child(props: { onOpen: () => void }) {
  return <button onClick={props.onOpen}>Open</button>
})

export function App() {
  const openFile = useCallback(async () => {
    await window.api.openDialog()
  }, [])
  return <Child onOpen={openFile} />
}
'''.lstrip()
    root = tmp_path
    path = root / "sample.tsx"
    path.write_text(source, encoding="utf-8")
    rec = record_from_bytes("sample.tsx", source.encode("utf-8"))

    result = TypeScriptElectronAdapter().extract(root, rec, source)
    function_names = {n.name for n in result.nodes if n.kind == "symbol" and (n.attributes or {}).get("symbol_role") == "function"}
    assert "Child" in function_names
    assert "openFile" in function_names

    child_prop = [n for n in result.nodes if n.kind == "handler_reference" and n.name == "Child.onOpen"]
    assert child_prop, "physical Child button and parent prop binding should share a semantic prop endpoint"

    open_symbols = [n for n in result.nodes if n.kind == "symbol" and n.name == "openFile"]
    assert len(open_symbols) == 1
    assert any(e.dst == open_symbols[0].id and e.kind == "resolves_to" for e in result.edges)

    preload = [n for n in result.nodes if n.kind == "handler_reference" and n.name == "preload:api.openDialog"]
    assert preload
    assert any(e.dst == preload[0].id and e.kind == "routes_to" for e in result.edges)
