# SCAN Engine v0.35

Status: **independent-reconstruction-proof candidate — not release-qualified**.

v0.35 is stacked on the v0.34 broader-calibration candidate and implements the seventh production-readiness stage: mechanically verifiable source-isolated reconstruction trials.

This stage does not add extraction rules or scanner adapters.

## Goal

A reconstruction result must be distinguishable from a reconstruction that merely *claims* it was blind.

The qualification path is split into three trust domains:

1. **Preparation** — SCAN verifies/certifies the private source and emits a sealed source-free reconstruction challenge plus a separate private evaluator.
2. **Independent worker** — a separate clean job receives only the public challenge. It has no repository checkout and no private evaluator. Candidate generation runs inside an enforced network namespace.
3. **Adjudication** — a separate trusted job receives the private evaluator and candidate, performs a fresh read-only SCAN of the candidate, seals the trial, and verifies the complete lineage.

The worker does not grade itself.

## Independent proof artifact

v0.35 adds:

```bash
scan-body verify-independent-reconstruction \
  challenge/ candidate/ submission.json worker_receipt.json trial/ \
  --out independent_proof.json
```

The verifier binds:

- the sealed public challenge manifest hash;
- the worker isolation receipt;
- the candidate tree hash;
- the submission hash and source-isolation declaration;
- the private reconstruction-trial lineage;
- the fresh candidate scan and scorecard.

A worker receipt passes only when it records:

- repository checkout: `ABSENT`;
- original source: `NOT_PRESENT`;
- private evaluator: `NOT_PRESENT`;
- input artifacts: exactly `["challenge"]`;
- worker network: mechanically disabled by an approved isolation mechanism.

A `DECLARED_ONLY` network state is insufficient.

## What a PASS means

A v0.35 independent proof PASS means:

- the public challenge was mechanically source-free and untampered;
- the reconstruction worker ran through the isolated handoff path;
- the candidate bytes match the worker receipt;
- SCAN independently rescanned the candidate;
- the private evaluator/trial lineage matches the public challenge;
- all mechanically scorable required reconstruction anchors passed.

It does **not** establish:

- runtime equivalence;
- pixel/visual equivalence;
- timing equivalence;
- universal behavioral equivalence;
- external-LLM quality or generality.

## Reference-worker qualification

The CI qualification uses a deterministic reference reconstruction worker. This is intentional.

Its purpose is to prove that the isolation, handoff, lineage, and independent-scoring machinery works end-to-end without depending on an external model service or secret API key.

The reference worker executes in a separate GitHub Actions job that:

- performs no repository checkout;
- downloads only the public challenge artifact;
- verifies private evaluator/source artifacts are absent;
- enters a Linux network namespace before candidate generation;
- records the candidate and submission hashes in a worker receipt.

The reference worker is **not** presented as an external LLM benchmark. Future external coding agents can occupy the same isolated worker slot and produce the same receipt/submission contract.

## Authority boundary

- candidate self-report: no scoring authority;
- worker receipt: proves handoff/isolation lineage, not correctness;
- private SCAN fresh scan: measurement authority;
- source uncertainty remains source uncertainty;
- candidate scanner gaps remain scanner-attributed;
- reconstruction failures remain reconstruction-attributed.

## Promotion gates

Before this stage is admitted:

1. all inherited tests remain green;
2. public challenge tampering/leakage is rejected;
3. worker receipt rejects declared-only network isolation;
4. candidate tampering breaks worker lineage;
5. separate-job CI worker has no checkout/evaluator/source access;
6. network isolation is mechanically enforced during worker execution;
7. fresh private scoring passes for the reference reconstruction;
8. final independent proof verifies challenge → worker → candidate → trial lineage;
9. no runtime/visual/timing or external-LLM benchmark claim is made.

The next roadmap stage is authorized runtime validation.

v0.28.0 remains the latest released version while stacked production-readiness candidates are evaluated.
