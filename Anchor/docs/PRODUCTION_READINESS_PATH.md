# SCAN / Anchor Code Production-Readiness Path

Status: active roadmap after released SCAN v0.28.0.

This document is a gate sequence, not a feature backlog. Only the active stage should add product behavior. A later stage does not begin until the current stage has objective evidence that its exit conditions hold.

The canonical authority remains `scan_index.sqlite`; derived reports, reviewers, rankings, scenarios, and external formats must never become competing truth stores.

## Stage 1 — Coverage / gaps

Status: **ACTIVE in Engine v0.29 candidate**.

Goal: make existing uncertainty immediately inspectable without manually mining the Blueprint or graph.

Outputs:

- `coverage_report.json`
- `coverage_report.md`
- `gaps.md`

Required properties:

- exact reconciliation to canonical files/nodes/edges/findings/semantic objects/relations/completeness;
- existing surface/effect closure reused rather than reimplemented;
- canonical IDs and evidence IDs retained;
- read-only projection generation;
- deterministic bytes for unchanged canonical evidence;
- no scalar confidence percentage;
- no evidence-state promotion/demotion.

Exit gate:

1. full v0.29 regression PASS;
2. duplicate projection bytes PASS;
3. canonical DB unchanged by projection generation;
4. v0.28 -> v0.29 canonical evidence parity on frozen specimens;
5. report counts reconcile exactly to SQLite;
6. frozen NotepadNext/Moji projection calibration PASS.

## Stage 2 — Uncertainty challenger

Status: BLOCKED on Stage 1.

Goal: adversarially interrogate PARTIAL/UNKNOWN/BLOCKED claims without granting a reviewer authority to change them.

The challenger may propose evidence searches, contradictions, missing joins, or parser/acquisition targets. Only deterministic SCAN evidence or an existing promotion gate may alter canonical state.

## Stage 3 — Triage ranking

Status: BLOCKED on Stage 2.

Goal: prioritize investigation under partial evidence using graph centrality plus human-surface reachability, effect reachability, artery participation, reconstruction-anchor dependency, and unresolved-state severity.

Ranking is investigation priority, never truth/confidence.

## Stage 4 — Layered provenance

Status: BLOCKED on Stage 3.

Goal: make the existing hierarchy explicit:

E0 direct evidence -> E1 mechanical anatomy -> E2 semantic interpretation -> E3 reconstruction contract -> E4 human explanation.

Each layer retains its own state and upstream proof links so uncertainty in interpretation does not erase certainty in mechanical facts.

## Stage 5 — Parity scenarios / distribution

Status: BLOCKED on Stage 4.

Goal: derive optional human/agent-readable parity scenarios from existing conformance contracts and add minimal distribution discovery such as an AGENTS.md pointer.

No second specification authority is allowed.

## Stage 6 — Broader calibration

Status: BLOCKED on Stage 5.

Goal: test the complete candidate across varied real and adversarial substrates, including incomplete acquisition, parser failure, mixed language/framework cases, persistence, extensions, and the frozen blind holdout.

## Stage 7 — Independent reconstruction proof

Status: BLOCKED on Stage 6.

Goal: hand sealed, source-free reconstruction packages to capable external coding agents, rescan their outputs, and mechanically attribute mismatches to scanner coverage, semantic IR/contracts, reconstruction agents, or unresolved source evidence.

## Stage 8 — Authorized runtime validation

Status: BLOCKED on Stage 7.

Goal: where explicitly authorized, validate behavior that static evidence cannot settle. Runtime observations remain a separate evidence class and never weaken A1 static defaults.

## Stage 9 — Operational hardening

Status: BLOCKED on Stage 8.

Goal: harden malformed/hostile inputs, resource ceilings, cancellation/resume, database corruption, concurrency, large repositories, and supported platform/Python combinations.

## Stage 10 — v1.0 certification

Status: BLOCKED on Stage 9.

Goal: freeze the supported scope and run the complete deterministic, calibration, reconstruction, runtime-where-authorized, security, packaging, and documentation gates without product patches between stages.

## Production-ready definition

SCAN/Anchor Code is production-ready when, for every declared supported substrate, it can safely and deterministically account for visible software, preserve provenance and uncertainty, generate reconstruction contracts without inventing facts, independently verify reconstructed candidates, survive realistic failure conditions, and ship reproducible auditable releases.

Production-ready does **not** mean zero UNKNOWNs. It means unknowns cannot silently disappear or become stronger claims without evidence.
