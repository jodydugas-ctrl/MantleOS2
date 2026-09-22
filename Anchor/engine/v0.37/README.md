# SCAN Engine v0.37

Status: **operational-hardening candidate — not release-qualified**.

v0.37 is stacked on the v0.36 authorized-runtime-validation candidate and implements the ninth production-readiness stage: operational hardening before final v1.0 certification.

The purpose of this stage is not to add another interpretation layer. It is to make the existing scanner fail predictably under hostile, malformed, interrupted, concurrent, oversized, or otherwise inconvenient operating conditions while preserving its evidence boundaries.

## New writer-safety boundary

Every canonical `scan` and `scan-manifest` operation now acquires an exclusive scanner-owned output lease:

`.scan-write.lock`

The lease:

- is created atomically with `O_CREAT | O_EXCL`;
- records schema, engine version, PID, host, and process-start token;
- refuses a second live writer targeting the same output directory;
- recovers a stale lock only when the previous writer is provably dead on the same host;
- fails closed for unreadable locks and foreign-host ownership;
- is released on ordinary completion and on propagated exceptions;
- rejects an output root that is itself a symlink.

The lease is operational metadata only. It is not canonical evidence and it is removed before a successful scan returns.

## Hardening coverage

The v0.37 regression and CI gates exercise the operational failure surface accumulated across earlier versions, including:

- malformed and non-UTF-8 repository content;
- parser/adaptor exceptions versus catastrophic `MemoryError`;
- local symlink containment and manifest path traversal;
- per-file and aggregate resource ceilings;
- extraction cancellation and safe-boundary partial completion;
- budget-limited resume using valid extraction cache;
- corrupt SQLite quarantine and clean rebuild;
- deterministic fresh rebuilds and projection hashes;
- exclusive output-writer behavior and stale-lock recovery;
- bounded synthetic large-repository degradation;
- clean wheel/CLI installation checks;
- Linux, macOS, and Windows execution of the focused hardening suite.

Inherited runtime-validation behavior remains unchanged: ordinary SCAN is static and non-executing; `runtime-validate` remains explicit, plan-hash authorized, network-denied, and sidecar-only.

## Failure semantics

Operational hardening keeps three classes distinct:

1. **Explicit degradation** — unsafe, unavailable, malformed, or resource-limited specimen regions remain visible as PARTIAL/BLOCKED/UNKNOWN states rather than disappearing.
2. **Recoverable scanner state failure** — derived-state corruption may be quarantined and mechanically rebuilt when the existing recovery policy authorizes it.
3. **Catastrophic process failure** — conditions such as `MemoryError` propagate instead of being mislabeled as ordinary parser uncertainty. Writer leases are still released by the caller boundary.

A hardening PASS therefore means the tested failure mode produced the expected bounded outcome. It does not mean every possible hostile repository or operating-system failure has been exhausted.

## Operational acceptance boundary

The v0.37 stage is intended to prove that:

- no specimen symlink/path-traversal case can escape the scanner's source authority boundary;
- concurrent writers cannot silently interleave one output tree;
- interrupted or crashed same-host writers do not permanently poison that output path;
- malformed inputs degrade explicitly rather than erasing the rest of the specimen;
- resource exhaustion controls remain coverage statements, not false-success claims;
- corrupt derived state can be distinguished from source evidence and recovered under the existing policy;
- unchanged fresh scans remain reproducible;
- focused hardening behavior survives the supported Python range and the three primary desktop CI operating systems.

## Explicit limits

This stage does **not** claim:

- hostile-code sandboxing beyond the already documented authorized-runtime isolation controls;
- distributed or multi-host writer coordination;
- correctness on network filesystems with weak/novel locking semantics;
- power-loss atomicity for every projection file on every storage stack;
- exhaustive fuzz coverage of every parser grammar;
- a production SLA for repository size, latency, CPU, or memory;
- universal GUI/visual/runtime equivalence;
- final v1.0 certification.

Those claims require evidence beyond this tranche.

The next and final roadmap stage is **v1.0 certification**.

v0.28.0 remains the latest released version while the stacked production-readiness candidates are evaluated.
