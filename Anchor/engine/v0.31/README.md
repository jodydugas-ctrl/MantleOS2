# SCAN Engine v0.31

Status: **triage-ranking integration candidate — not release-qualified**.

v0.31 is stacked on the v0.30 uncertainty challenger and implements only the third production-readiness stage: deterministic investigation triage.

## Purpose

The triage layer answers one operational question:

> Which unresolved gaps are most useful to investigate first?

It does **not** answer which claims are more true, more confident, or eligible for promotion.

Ordinary scans emit:

- `triage_ranking.json`
- `triage_ranking.md`

The same ranking can be regenerated from an existing canonical database:

```bash
scan-body triage-gaps .scan/scan_index.sqlite --out-dir ./triage
```

## Transparent scoring

The maximum investigation score is 100 points, composed only from explicit graph-impact signals:

- structural connectivity: 20 max;
- reachable actionable human surfaces: 30 max;
- reachable effect/state/NEST/feedback terminals: 20 max;
- reconstruction-anchor dependency: 20 max;
- challenger mechanical-recheck support: 10 max.

Every component and raw count is emitted in the JSON report.

Coverage state and gap category are **not scoring weights**. A `BLOCKED` item does not automatically rank above or below a `PARTIAL` item.

Structural connectivity is capped at 20 points so generic utilities, dispatchers, logging hubs, or framework wrappers cannot dominate the ranking simply because many edges touch them.

## Authority boundary

The ranking is downstream operational metadata only:

- `importance_not_truth = true`
- `confidence_effect = NONE`
- `promotion_effect = NONE`
- `canonical_write_allowed = false`
- `llm_required = false`

Ranking never changes the gap, challenge, evidence, coverage, or conformance state.

## Explicit non-goals

This tranche does not add:

- confidence scoring;
- evidence promotion;
- layered provenance schema changes;
- parity scenarios;
- AGENTS.md distribution;
- runtime execution;
- calibration expansion.

Those remain later roadmap stages.

## Promotion gates

Before this stage is admitted:

1. all inherited v0.30 tests remain green;
2. triage output is deterministic;
3. regeneration from a read-only DB does not mutate canonical bytes;
4. every investigation score equals the sum of emitted components and stays within 0..100;
5. ranking is sorted deterministically with stable tie-breaking;
6. graph-impact tests prove a load-bearing unresolved node outranks an isolated unresolved node without state weighting;
7. a high-degree generic hub is capped and cannot dominate solely through degree;
8. projection metadata explicitly states that importance has no confidence or promotion effect.

v0.28.0 remains the latest released SCAN version while the stacked production-readiness candidates are evaluated.
