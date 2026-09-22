# SCAN Engine v0.33

Status: **parity-scenarios/distribution integration candidate — not release-qualified**.

v0.33 is stacked on the v0.32 layered-provenance candidate and implements only the fifth production-readiness stage: portable static parity scenarios plus lightweight agent discovery.

## Purpose

The parity layer turns the Blueprint's existing embedded conformance manifest into human/agent-readable Given/When/Then scenarios without creating a second specification.

Only contracts that are both:

- `coverage = MAPPED`
- `enforcement = REQUIRED`

become parity scenarios.

PARTIAL, BLOCKED, UNKNOWN, and advisory observations remain outside binary parity requirements.

## Portable outputs

Every Anchor Blueprint export now produces companion files in the same distribution directory:

- `parity_scenarios.json`
- `parity_scenarios.feature`
- `AGENTS.md` when no project-authored AGENTS file already exists

The same package can be regenerated from the Blueprint alone:

```bash
scan-body parity-scenarios "Application Anchor Blueprint.md" --out-dir ./handoff
```

No source repository or `scan_index.sqlite` is required for regeneration.

## Scenario authority

Each parity scenario references exactly one embedded conformance contract ID.

The scenario means only:

1. a reconstruction candidate exists;
2. SCAN performs a fresh read-only candidate scan;
3. the source contract must be reported `SATISFIED`.

The scenarios explicitly do **not** claim runtime, visual/pixel, timing, network, performance, or behavioral equivalence beyond what static conformance mechanically establishes.

Scenario JSON retains the original contract identity, expected values, comparison rule, count, and source references. The Gherkin file is a readable rendering of that same projection.

## AGENTS.md distribution

The generated AGENTS pointer is intentionally small. It:

- points to the authoritative Blueprint;
- records the Blueprint SHA-256;
- identifies the parity files as derived projections;
- instructs agents to verify with a fresh SCAN conformance pass;
- states that candidate self-report is not evidence;
- preserves uncertainty;
- repeats that static parity is not runtime equivalence.

SCAN never replaces an existing project-authored `AGENTS.md`. If a non-SCAN AGENTS file already exists, it is preserved unchanged and the distribution result reports `PRESERVED_EXISTING`.

## Authority boundary

- Blueprint embedded conformance manifest remains authoritative for portable static contracts;
- parity scenarios are projections only;
- parity scenarios cannot add requirements;
- candidate self-report has no authority;
- AGENTS.md is discovery/instruction metadata, not a specification;
- runtime equivalence is deferred to the later authorized runtime-validation stage.

## Explicit non-goals

This tranche does not add:

- new conformance contracts;
- runtime scenarios;
- visual/pixel assertions;
- timing assertions;
- broader calibration;
- reconstruction scoring changes;
- runtime execution;
- evidence promotion.

## Promotion gates

Before this stage is admitted:

1. all inherited v0.32 tests remain green;
2. every parity scenario maps 1:1 to an embedded MAPPED+REQUIRED contract;
3. advisory and uncertain contracts never become required parity scenarios;
4. parity regeneration from the portable Blueprint is deterministic;
5. parity regeneration does not modify the Blueprint;
6. the Gherkin file contains exactly one scenario per JSON scenario;
7. `AGENTS.md` remains small and contains no copied contract list;
8. an existing project-authored `AGENTS.md` is never overwritten;
9. scenario metadata explicitly states that runtime/visual/timing equivalence is not claimed.

v0.28.0 remains the latest released SCAN version while the stacked production-readiness candidates are evaluated.
