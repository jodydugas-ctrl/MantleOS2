# SCAN v1.0 Certification Contract

Status: **final release-candidate certification contract**.

v1.0 is the consolidation stage for the production-readiness path:

coverage/gaps → uncertainty challenger → triage ranking → layered provenance → parity scenarios/distribution → broader calibration → independent reconstruction proof → authorized runtime validation → operational hardening → v1.0 certification.

The purpose of this stage is to certify a specific set of package bytes and a specific CI-tested commit. It does not add new semantic authority to SCAN.

## Two-layer certification

The final release uses two deliberately separate layers.

### 1. Local mechanical package certificate

`scan-body release-certify <package-root> --out <certification-dir>`

requires an already sealed `PACKAGE_MANIFEST.json` and then:

- verifies every package file, byte count, and SHA-256;
- verifies runtime/package/pyproject version agreement;
- runs the packaged LLM-disabled release qualification;
- requires all current canonical projection families, including:
  - coverage and gaps;
  - uncertainty challenges;
  - triage ranking;
  - layered provenance;
- runs the release query surface and integrity gates;
- records the exact package-manifest SHA-256;
- records the exact qualification-report SHA-256;
- seals the local certificate and qualification in `V1_RELEASE_MANIFEST.json`;
- verifies the sealed result before returning PASS.

This certificate has scope `LOCAL_MECHANICAL_PACKAGE`.

A local PASS is intentionally **not** the final CI release certificate. It cannot prove operating-system matrix results or a live network-namespace runtime gate merely by inspecting local files.

### 2. CI release certificate

The v1.0 GitHub Actions release gate runs against one exact commit and requires:

- full inherited regression suite PASS;
- focused v1.0/v0.37 hardening tests on Linux, macOS, and Windows;
- Python 3.11, 3.12, and 3.13 matrix coverage;
- clean wheel build and fresh-environment installation;
- a real Linux `network=DENY` authorized-runtime validation;
- wrong-plan-hash refusal before execution;
- source immutability and secret non-forwarding during runtime validation;
- local mechanical package certification PASS;
- final artifact hashing and sealing.

The aggregate CI certificate may be emitted only after every prerequisite job has succeeded.

## Evidence semantics

The final certificate binds:

- engine version;
- Git commit SHA;
- exact package manifest SHA-256;
- local release-certificate manifest SHA-256;
- wheel SHA-256;
- regression count;
- platform matrix;
- live runtime-validation state;
- final artifact manifest.

The certificate does **not** convert a tested observation into a universal claim.

In particular, v1.0 certification does not imply:

- complete semantic understanding of every repository;
- universal runtime or visual equivalence;
- hostile-code sandbox security;
- distributed/multi-host write locking;
- correctness on every network filesystem;
- exhaustive fuzz coverage of every language grammar;
- an unbounded performance or memory guarantee;
- absence of future defects.

## Release invariant

A v1.0 release artifact is certified only when all required gates refer to the same release commit and the same sealed package bytes.

If code changes after certification, the package hash changes and the previous certification no longer applies.

## Release artifacts

The final workflow emits a release evidence bundle containing, at minimum:

- the sealed v1.0 package tree;
- `PACKAGE_MANIFEST.json`;
- local package certification;
- `V1_CI_RELEASE_CERTIFICATE.json`;
- `V1_CI_MANIFEST.json`;
- the built wheel and its SHA-256.

The evidence bundle is a release record, not a claim that unknown behavior no longer exists.
