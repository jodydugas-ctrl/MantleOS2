# SCAN Engine v1.0

Status: **final certification candidate**.

v1.0 is the consolidation release for the production-readiness path:

**coverage/gaps → uncertainty challenger → triage ranking → layered provenance → parity scenarios/distribution → broader calibration → independent reconstruction proof → authorized runtime validation → operational hardening → v1.0 certification**

The final stage does not add another interpretation layer. It binds an exact package, exact commit, mechanical qualification, cross-platform regression matrix, live authorized-runtime evidence, and release artifacts into one auditable release record.

## Final certification model

v1.0 separates local package proof from CI-wide release proof.

### Local package proof

A staged package must first be sealed:

```bash
scan-body package-manifest <package-root>
```

Then:

```bash
scan-body release-certify <package-root> --out <certification-dir>
scan-body verify-release-certification <certification-dir>
```

The local certificate:

- verifies every file against `PACKAGE_MANIFEST.json`;
- requires engine/package/pyproject version agreement;
- reruns the LLM-disabled mechanical release qualification;
- requires current coverage/gap, uncertainty, triage, and layered-provenance projections;
- seals the exact package-manifest and qualification hashes;
- verifies its own sealed output.

Its scope is explicitly `LOCAL_MECHANICAL_PACKAGE`.

A local PASS is not allowed to imply the CI-only release gates passed.

### CI release proof

The final v1.0 workflow additionally requires:

- the complete inherited regression suite;
- focused hardening/certification tests across Linux, macOS, and Windows;
- Python 3.11, 3.12, and 3.13 coverage;
- clean wheel build and fresh-environment install;
- live Linux `network=DENY` authorized-runtime validation;
- wrong-plan-hash fail-closed behavior;
- runtime source immutability and secret non-forwarding;
- the sealed local package certificate;
- final artifact hashing.

Only the aggregate CI gate may emit the final `V1_CI_RELEASE_CERTIFICATE.json`.

## Preserved authority boundaries

v1.0 retains all earlier boundaries:

- ordinary SCAN is static, deterministic, and non-executing;
- runtime execution requires explicit plan-hash authorization;
- runtime observations remain sidecar evidence and cannot automatically promote static claims;
- ranking is investigation priority, not truth;
- semantic overlays never become DIRECT evidence merely because an LLM proposed them;
- independent reconstruction proof remains distinct from ordinary reconstruction self-report;
- operational locks are scanner metadata, not canonical specimen evidence;
- budget stops and unavailable content remain explicit coverage limitations.

## Operational hardening retained

The v0.37 writer-safety behavior is inherited unchanged:

- one canonical writer per output tree;
- stale same-host dead-PID recovery;
- fail-closed ambiguous/foreign-host lock handling;
- Windows-safe process-liveness probing;
- output-root symlink rejection;
- exception-safe lease release.

## Certification limits

A v1.0 PASS does not claim:

- universal semantic completeness;
- universal runtime or pixel equivalence;
- hostile-code sandbox security;
- distributed/multi-host locking;
- correctness on every network filesystem;
- exhaustive parser fuzzing;
- an unbounded repository-size, memory, or latency SLA;
- absence of future defects.

The certificate applies to the exact sealed package bytes and commit that were tested.

See `docs/V1_CERTIFICATION.md` for the release contract.
