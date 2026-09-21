# SCAN Anchor

This directory is the GitHub home for the independent SCAN evidence-first software reverse-engineering project. It is stored within MantleOS2 for a possible future integration, but is not part of the MantleOS2 package, release, default tests, or product CodeQL analysis. Integration must be explicit; repository placement alone does not admit scanner code into MantleOS2.

The living canonical documents are maintained in Google Drive at:

`G:\My Drive\AI Systems\ANCHORCODING`

The Markdown files in this directory are synchronized repository copies. Updates should preserve the existing Google Drive file identities, then update these copies in the same development change so the governance contract, protocol, evidence report, and roadmap do not drift.

## Current checkpoint

- SCAN Engine: v0.25 frozen calibration release; v0.20 remains the immutable pre-oracle cold baseline
- Project documentation: v0.31 checkpoint (A1-A8 governing contract unchanged)
- Status: frozen pre-v1 candidate; calibration loop active, production certification pending
- PR5 NotepadNext calibration: v0.20 cold and v0.21-v0.25 sealed reruns mechanically PASS; calibration PARTIAL
- PR7 reconstruction proof: partial; M5 and M6A mechanisms pass, external-agent M6B remains open
- H-001 blind holdout: frozen and source-uninspected

## Documents

- [`ANCHOR_CODING_PROMPT.md`](ANCHOR_CODING_PROMPT.md) — governing A1-A8 architecture and evidence contract.
- [`SCAN_PROTOCOL.md`](SCAN_PROTOCOL.md) — operational scanning, certification, promotion, and reconstruction protocol.
- [`SCAN_REPORT.md`](SCAN_REPORT.md) — executed evidence, specimen findings, calibration history, and honest coverage state.
- [`SCAN_CREATION_PLAN.md`](SCAN_CREATION_PLAN.md) — engineering roadmap and PR1-PR8 certification ledger.
- [`evidence/pr5/PR5_ACQUISITION_RECEIPT.md`](evidence/pr5/PR5_ACQUISITION_RECEIPT.md) — exact pinned-source acquisition and archive digest evidence.
- [`evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json`](evidence/pr5/PR5_EXECUTION_ARTIFACT_REQUIREMENTS.json) — authoritative v0.20 release hashes and cold-run admission policy.
- [`evidence/pr5/PR5_COLD_SCAN_RECEIPT.json`](evidence/pr5/PR5_COLD_SCAN_RECEIPT.json) — sealed cold-run identity, coverage, and bundle digests.
- [`evidence/pr5/PR5_CALIBRATION_REPORT.md`](evidence/pr5/PR5_CALIBRATION_REPORT.md) — post-seal machine-versus-oracle comparison and generic corrective backlog.
- [`engine/v0.25/`](engine/v0.25/) — exact frozen combined adaptive/bounded scanner source; this is not the NotepadNext specimen.
- [`releases/v0.25/`](releases/v0.25/) — frozen v0.25 artifacts, deterministic/cache receipts, and completed PR5 certification/calibration evidence. The 277 MB sealed specimen bundle is kept out of Git and identified by SHA-256.

## Synchronization rules

1. Update the Drive documents in place; do not replace them with newly created files.
2. Mirror the same document bytes into this directory as part of the corresponding implementation or release change.
3. Keep aspirations in the creation plan and executed evidence in the report.
4. Do not promote `UNKNOWN`, `PARTIAL`, or `BLOCKED` findings into completed claims.
5. Do not alter A1-A8 merely to describe an implementation change.
6. Record only tests, scans, calibrations, and certifications that were actually executed.
