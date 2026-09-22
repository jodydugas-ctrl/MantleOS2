# SCAN Anchor

This directory is the GitHub home for the independent SCAN evidence-first software reverse-engineering project. It is stored within MantleOS2 for a possible future integration, but is not part of the MantleOS2 package, release, default tests, or product CodeQL analysis. Integration must be explicit; repository placement alone does not admit scanner code into MantleOS2.

The public, versioned project documents live in [`docs/`](docs/). They are part of this repository and are the only documentation paths referenced by this README.

## Current checkpoint

- SCAN Engine: **v0.28.0 released**; v0.29 is the active production-readiness candidate.
- v0.29 current tranche: deterministic coverage/gaps projection only; later uncertainty-challenger and triage stages are not yet admitted.
- v0.28 release qualification: 158 tests passed, 90/90 sealed package files verified, 12/12 release queries passed, LLM-disabled mechanical qualification PASS.
- v0.28 frozen calibration: NotepadNext 380 -> 380 actionable surfaces; Moji 103 -> 103; zero new actionable static-web surfaces; zero integrity errors.
- H-001 blind holdout remains frozen/source-uninspected until the broader-calibration stage.
- A1-A8 remain the governing architecture contract.

## Documents

- [`docs/ANCHOR_CODING_PROMPT.md`](docs/ANCHOR_CODING_PROMPT.md) — governing A1-A8 architecture and evidence contract.
- [`docs/SCAN_PROTOCOL.md`](docs/SCAN_PROTOCOL.md) — operational scanning, certification, promotion, and reconstruction protocol.
- [`docs/SCAN_REPORT.md`](docs/SCAN_REPORT.md) — executed evidence, specimen findings, calibration history, and honest coverage state.
- [`docs/SCAN_CREATION_PLAN.md`](docs/SCAN_CREATION_PLAN.md) — engineering roadmap and PR1-PR8 certification ledger.
- [`docs/PRODUCTION_READINESS_PATH.md`](docs/PRODUCTION_READINESS_PATH.md) — staged post-v0.28 path from coverage/gaps through v1.0 certification.
- [`evidence/pr5/PR5_ACQUISITION_RECEIPT.md`](evidence/pr5/PR5_ACQUISITION_RECEIPT.md) — exact pinned-source acquisition and archive digest evidence.
- [`evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json`](evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json) — authoritative v0.20 release hashes and cold-run admission policy.
- [`evidence/pr5/PR5_COLD_SCAN_RECEIPT.json`](evidence/pr5/PR5_COLD_SCAN_RECEIPT.json) — sealed cold-run identity, coverage, and bundle digests.
- [`evidence/pr5/PR5_CALIBRATION_REPORT.md`](evidence/pr5/PR5_CALIBRATION_REPORT.md) — post-seal machine-versus-oracle comparison and generic corrective backlog.
- [`engine/v0.26/`](engine/v0.26/) — exact frozen surface-denominator-corrected scanner source; this is not the NotepadNext specimen.
- [`engine/v0.28/`](engine/v0.28/) — released v0.28 scanner/reconstruction-verification engine.
- [`releases/v0.28/`](releases/v0.28/) — v0.28 sealed qualification, frozen-calibration, manifest, and release evidence.
- [`engine/v0.29/`](engine/v0.29/) — active coverage/gaps production-readiness candidate; not released or package-sealed.

## Synchronization rules

1. Update the tracked documents in `docs/` as part of the corresponding implementation or release change.
2. Keep documentation links repository-relative and usable by every reader.
3. Keep aspirations in the creation plan and executed evidence in the report.
4. Do not promote `UNKNOWN`, `PARTIAL`, or `BLOCKED` findings into completed claims.
5. Do not alter A1-A8 merely to describe an implementation change.
6. Record only tests, scans, calibrations, and certifications that were actually executed.
