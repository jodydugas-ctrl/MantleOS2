# SCAN Engine v0.29

Status: **coverage/gaps integration candidate — not release-qualified**.

v0.29 starts the production-readiness upgrade path from the sealed v0.28.0 release. This tranche adds only the first planned step: deterministic coverage and unresolved-gap projections.

## Added in this tranche

Ordinary scans now emit:

- `coverage_report.json`
- `coverage_report.md`
- `gaps.json`
- `gaps.md`

These artifacts are projections of `scan_index.sqlite`. They do not create a second authority, assign scalar confidence, rank gaps, or promote evidence.

The report reconciles existing canonical state across:

- files, nodes, edges, findings;
- semantic objects and relations;
- completeness dimensions;
- acquisition/content availability;
- human-surface closure;
- deep effect closure.

Each gap record carries a canonical object ID, state, reason code, evidence IDs when available, and a resolution target.

The same projections can be regenerated without rescanning:

```bash
scan-body coverage-gaps .scan/scan_index.sqlite --out-dir ./coverage
```

## Explicit non-goals

This tranche does **not** implement:

- uncertainty challenger/reviewer behavior;
- centrality or triage ranking;
- layered provenance changes;
- parity-scenario generation;
- AGENTS.md distribution;
- new runtime observation;
- any new evidence-promotion mechanism.

Those remain later production-readiness stages and must be admitted separately after this projection proves deterministic and useful.

## Promotion gates

Before this candidate advances:

1. focused coverage/gaps tests pass;
2. full v0.29 regression suite passes;
3. ordinary scan outputs remain deterministic;
4. coverage counts reconcile exactly to the canonical database;
5. regeneration from a read-only DB does not mutate canonical bytes;
6. v0.28 calibration behavior is not regressed;
7. no stale package manifest is carried forward.

Until those gates are executed, v0.28.0 remains the latest released SCAN version.
