# SCAN Engine v0.29

Status: **development candidate — coverage/gaps tranche only**.

v0.29 begins the production-readiness path from released v0.28. This tranche adds one capability only: a deterministic coverage and unresolved-gap projection over the existing canonical SCAN database and closure calculations.

No uncertainty challenger, triage ranking, layered-provenance redesign, parity scenarios, or other later roadmap stages are included here.

## Authority model

The authority remains:

`scan_index.sqlite -> derived projections`

The new coverage/gaps outputs cannot write to the canonical database, cannot upgrade or downgrade MAPPED/PARTIAL/BLOCKED/UNKNOWN, and do not calculate a scalar confidence score.

The projection exists to answer two operational questions without manually mining a Blueprint:

1. What does SCAN currently know, layer by layer?
2. What remains unresolved, and which canonical object/evidence IDs should be investigated?

## New outputs

Every ordinary scan emits:

- `coverage_report.json` — complete machine-readable rollup and gap ledger;
- `coverage_report.md` — compact human/agent coverage summary;
- `gaps.md` — unresolved canonical-ID checklist with evidence references and deterministic next-evidence guidance.

The report reconciles:

- files;
- mechanical nodes;
- mechanical edges;
- findings;
- semantic objects;
- semantic relations;
- completeness dimensions;
- evidence classes/extractors;
- acquisition availability;
- human-surface binding closure;
- surface-to-effect/state/NEST/feedback closure.

Explicit regeneration is also available:

```bash
scan-body coverage-report .scan/scan_index.sqlite --out-dir .scan
```

## Non-goals

This tranche does **not**:

- reinterpret source;
- run an LLM;
- review or challenge uncertainty;
- rank gaps by importance;
- add another graph/database;
- create a scalar confidence percentage;
- change the A1-A8 governance anchors.

Those belong to later stages only after this projection is mechanically proven.

## Promotion gates

Before this tranche can be accepted:

1. full v0.29 regression suite passes;
2. coverage counts reconcile exactly with canonical SQLite rows;
3. projection generation leaves the SQLite database byte-identical;
4. repeated projection generation is byte deterministic;
5. ordinary scans automatically emit and seal all three new projections;
6. v0.28 and v0.29 canonical scan rows remain identical on the same fixture;
7. release qualification requires the new outputs;
8. no inherited v0.28 package manifest is present.

v0.28 remains the released line until v0.29 completes its own later release process.
