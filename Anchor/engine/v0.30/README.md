# SCAN Engine v0.30

Status: **uncertainty-challenger integration candidate — not release-qualified**.

v0.30 is stacked on the v0.29 coverage/gaps candidate and implements only the second production-readiness stage: a read-only uncertainty challenger.

## Purpose

The challenger interrogates unresolved `PARTIAL`, `UNKNOWN`, `BLOCKED`, and closure gaps after the deterministic coverage projection is generated.

It does not re-grade SCAN, assign confidence, promote evidence, or write canonical state.

For each gap it may surface:

- directly attached evidence IDs;
- one-hop graph relations and neighboring objects;
- MAPPED neighboring objects that may justify a mechanical recheck;
- semantic relations already present in the canonical evidence graph;
- a deterministic challenge kind;
- a named list of mechanical checks that could resolve or further bound the gap.

Ordinary scans emit:

- `uncertainty_challenges.json`
- `uncertainty_challenges.md`

The same second pass can be regenerated from an existing database:

```bash
scan-body challenge-uncertainty .scan/scan_index.sqlite --out-dir ./challenge
```

## Authority boundary

The challenger is deliberately powerless over canonical state:

- `canonical_write_allowed = false`
- `promotion_allowed = false`
- no `new_state` or `promoted_state` field exists;
- no scalar confidence is generated;
- no priority, score, or rank is generated;
- a state change still requires a deterministic rescan or an already-governed promotion gate.

This keeps the later triage-ranking stage separate from evidence review.

## Challenge classes

The initial deterministic vocabulary is:

- `BLOCKED_ON_ACQUISITION`
- `PARSER_COVERAGE_REQUIRED`
- `RECHECK_LOCAL_GRAPH`
- `RECHECK_SURFACE_ROUTE`
- `RECHECK_EFFECT_ROUTE`
- `RECHECK_COMPLETENESS_DEPENDENCIES`
- `REVIEW_RECORDED_FINDING`

Dispositions distinguish external-input blockers, scanner-work requirements, available mechanical rechecks, and gaps where no local support was found.

## Explicit non-goals

This tranche does not add:

- centrality or triage ranking;
- layered provenance schema changes;
- parity scenarios;
- AGENTS.md distribution;
- runtime execution;
- autonomous LLM authority;
- any new evidence-promotion path.

## Promotion gates

Before this stage is admitted:

1. all inherited v0.29 coverage/gaps tests remain green;
2. full v0.30 regression suite passes;
3. challenger output is deterministic;
4. regeneration from a read-only DB does not mutate canonical bytes;
5. every candidate evidence ID exists in the canonical evidence table;
6. every challenge references an existing projected gap;
7. blocked acquisition remains blocked rather than being semantically reclassified;
8. local mapped-neighbor support can produce a mechanical recheck proposal without changing canonical state.

v0.28.0 remains the latest released SCAN version until the stacked candidates complete later release qualification.
