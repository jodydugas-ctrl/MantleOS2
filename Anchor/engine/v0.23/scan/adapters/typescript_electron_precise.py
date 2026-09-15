from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from .typescript_electron import TypeScriptElectronAdapter as _BaseTypeScriptElectronAdapter
from ..inventory import FileRecord
from ..model import Edge, ExtractionResult, Finding, Node, stable_id


class TypeScriptElectronAdapter(_BaseTypeScriptElectronAdapter):
    """TypeScript/Electron adapter with source-location identity for individual call sites.

    The first generic TypeScript adapter intentionally modeled API identity aggressively, but that
    caused repeated calls such as ``ipcRenderer.invoke(...)`` in one file to share one structural
    node. Distinct channels could then meet at that merged node and create impossible behavior paths.

    This refinement keeps raw call sites distinct by file/line before SCAN performs higher-level
    graph synthesis. API aggregation remains available through names/effects/capabilities, while
    provenance paths cannot cross between unrelated invocations merely because they call the same API.
    """

    name = "typescript-electron"
    version = "2"

    def extract(self, root: Path, record: FileRecord, text: str) -> ExtractionResult:
        result = super().extract(root, record, text)
        return self._preserve_callsite_identity(record, result)

    @staticmethod
    def _evidence_lines(result: ExtractionResult) -> dict[str, int | None]:
        return {ev.id: ev.start_line for ev in result.evidence}

    def _preserve_callsite_identity(self, record: FileRecord, result: ExtractionResult) -> ExtractionResult:
        evidence_line = self._evidence_lines(result)
        call_nodes = [n for n in result.nodes if n.kind == "call_reference"]
        if not call_nodes:
            return result

        grouped: dict[str, list[Node]] = defaultdict(list)
        for n in call_nodes:
            grouped[n.id].append(n)

        # Every raw call site receives a location-sensitive ID, even when there was only one
        # occurrence. This makes the identity rule explicit and stable for later scans.
        site_map: dict[str, dict[int | None, str]] = defaultdict(dict)
        replacements: list[Node] = []
        kept_non_calls = [n for n in result.nodes if n.kind != "call_reference"]

        def node_line(n: Node) -> int | None:
            lines = {evidence_line.get(eid) for eid in n.evidence_ids if evidence_line.get(eid) is not None}
            if len(lines) == 1:
                return next(iter(lines))
            value = (n.attributes or {}).get("line")
            return value if isinstance(value, int) else None

        for old_id, nodes in grouped.items():
            by_line: dict[int | None, list[Node]] = defaultdict(list)
            for n in nodes:
                by_line[node_line(n)].append(n)
            for line, same_site in by_line.items():
                exemplar = same_site[0]
                attrs: dict[str, Any] = dict(exemplar.attributes or {})
                attrs["callsite_line"] = line
                attrs["identity_rule"] = "file+callee+source-line"
                ev_ids = sorted({eid for n in same_site for eid in n.evidence_ids})
                new_id = stable_id("call_reference", record.id, attrs.get("callee") or exemplar.name, line)
                site_map[old_id][line] = new_id
                replacements.append(Node(
                    new_id, "call_reference", exemplar.name, exemplar.file_id, exemplar.path,
                    exemplar.coverage, attrs, ev_ids,
                ))

        def edge_line(edge: Edge) -> int | None:
            lines = {evidence_line.get(eid) for eid in edge.evidence_ids if evidence_line.get(eid) is not None}
            if len(lines) == 1:
                return next(iter(lines))
            return None

        findings = list(result.findings)
        rebuilt_edges: list[Edge] = []
        for edge in result.edges:
            src_sites = site_map.get(edge.src)
            dst_sites = site_map.get(edge.dst)
            if not src_sites and not dst_sites:
                rebuilt_edges.append(edge)
                continue

            line = edge_line(edge)

            def resolve(endpoint: str, sites: dict[int | None, str] | None) -> str | None:
                if not sites:
                    return endpoint
                if line in sites:
                    return sites[line]
                if len(sites) == 1:
                    return next(iter(sites.values()))
                return None

            new_src = resolve(edge.src, src_sites)
            new_dst = resolve(edge.dst, dst_sites)
            if new_src is None or new_dst is None:
                findings.append(Finding(
                    stable_id("finding", record.id, self.name, self.version, "ambiguous-callsite-edge", edge.id),
                    "resolution_gap",
                    f"Could not assign structural edge to one {record.language} call site",
                    "PARTIAL",
                    {
                        "old_edge_id": edge.id,
                        "edge_kind": edge.kind,
                        "source_callsite_count": len(src_sites or {}),
                        "target_callsite_count": len(dst_sites or {}),
                        "edge_evidence_lines": sorted({x for x in (evidence_line.get(eid) for eid in edge.evidence_ids) if x is not None}),
                        "meaning": "edge omitted rather than allowing unrelated repeated calls to share a behavior path",
                    },
                    list(edge.evidence_ids),
                ))
                continue

            rebuilt_edges.append(Edge(
                stable_id("edge", new_src, edge.kind, new_dst, record.id, line),
                new_src, new_dst, edge.kind, edge.coverage,
                dict(edge.attributes or {}), list(edge.evidence_ids),
            ))

        result.nodes = kept_non_calls + replacements
        result.edges = rebuilt_edges
        result.findings = findings
        return result
