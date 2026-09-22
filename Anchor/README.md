# SCAN Anchor

This directory is the GitHub home for the independent SCAN evidence-first
software reverse-engineering project. It is stored within MantleOS2 for possible
future integration, but it is not part of the MantleOS2 package, default tests,
or product authority model. Repository placement alone does not admit scanner
code into MantleOS2.

The public project contract and evidence history live in [`docs/`](docs/).
Versioned engine source lives in [`engine/`](engine/). Historical frozen
release/calibration records live in [`releases/`](releases/).

## Current checkpoint

- SCAN Engine: **v1.0.0 certified release package**
- Current source: [`engine/v1.0/`](engine/v1.0/README.md)
- Production-readiness path: **complete through v1.0 certification**
- Final local package certificate: exact-byte / manifest bound
- Final CI gate: full inherited regression, Linux/macOS/Windows matrix,
  independent-reconstruction regression, live authorized runtime validation,
  operational hardening, clean wheel installation, and aggregate artifact
  sealing
- Ordinary SCAN remains static and non-executing; runtime execution remains
  explicit plan-hash-authorized sidecar validation only
- PR5 NotepadNext calibration remains **PARTIAL** as specimen-specific evidence;
  v1.0 certification does not convert its unresolved semantic/behavioral gaps
  into certainty
- v0.20 remains the immutable pre-oracle cold baseline
- v0.28 remains the final frozen pre-v1 release lineage retained for comparison

The v1.0 certificate is commit- and byte-specific. A source change, merge result,
or rebuilt package must rerun the final certification gate before that new
revision inherits the certified status.

## Production-readiness roadmap

The completed v1.0 path is:

`coverage/gaps → uncertainty challenger → triage ranking → layered provenance → parity scenarios/distribution → broader calibration → independent reconstruction proof → authorized runtime validation → operational hardening → v1.0 certification`

The stages are deliberately layered. Later projections do not silently acquire
more evidence authority than the canonical graph from which they are derived.

## Current v1.0 entry points

- [`engine/v1.0/README.md`](engine/v1.0/README.md) — v1.0 package and authority boundaries.
- [`engine/v1.0/docs/V1_CERTIFICATION.md`](engine/v1.0/docs/V1_CERTIFICATION.md) — final certification contract.
- [`engine/v1.0/docs/RELEASE_QUALIFICATION.md`](engine/v1.0/docs/RELEASE_QUALIFICATION.md) — mechanical qualification surface.
- [`docs/ANCHOR_CODING_PROMPT.md`](docs/ANCHOR_CODING_PROMPT.md) — governing A1-A8 architecture and evidence contract.
- [`docs/SCAN_PROTOCOL.md`](docs/SCAN_PROTOCOL.md) — operational scanning, certification, promotion, and reconstruction protocol.
- [`docs/SCAN_REPORT.md`](docs/SCAN_REPORT.md) — executed evidence, specimen findings, calibration history, and current release checkpoint.
- [`docs/SCAN_CREATION_PLAN.md`](docs/SCAN_CREATION_PLAN.md) — engineering roadmap and certification ledger.
- [`releases/README.md`](releases/README.md) — frozen historical releases and current release-record policy.

## Historical evidence

- [`evidence/pr5/PR5_ACQUISITION_RECEIPT.md`](evidence/pr5/PR5_ACQUISITION_RECEIPT.md) — pinned-source acquisition evidence.
- [`evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json`](evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json) — authoritative v0.20 cold-run admission policy.
- [`evidence/pr5/PR5_COLD_SCAN_RECEIPT.json`](evidence/pr5/PR5_COLD_SCAN_RECEIPT.json) — sealed cold-run identity and bundle digests.
- [`evidence/pr5/PR5_CALIBRATION_REPORT.md`](evidence/pr5/PR5_CALIBRATION_REPORT.md) — post-seal machine-versus-oracle comparison.
- [`engine/v0.26/`](engine/v0.26/) and [`releases/v0.26/`](releases/v0.26/) — frozen surface-denominator-corrected historical scanner and calibration evidence.
- [`engine/v0.28/`](engine/v0.28/) and [`releases/v0.28/`](releases/v0.28/) — last frozen pre-v1 release lineage.

## Synchronization rules

1. Update tracked public documents as part of the corresponding implementation or release change.
2. Keep documentation links repository-relative and usable by every reader.
3. Keep aspirations in the creation plan and executed evidence in the report.
4. Do not promote `UNKNOWN`, `PARTIAL`, or `BLOCKED` findings into completed claims.
5. Do not alter A1-A8 merely to describe an implementation change.
6. Record only tests, scans, calibrations, runtime observations, and certifications that were actually executed.
7. Treat release certification as exact-commit/exact-byte evidence; rerun it after any change that affects the certified revision.
