# SCAN Anchor

This directory is the GitHub home for the SCAN evidence-first software reverse-engineering project within MantleOS2.

The living canonical documents are maintained in Google Drive at:

`G:\My Drive\AI Systems\ANCHORCODING`

The Markdown files in this directory are synchronized repository copies. Updates should preserve the existing Google Drive file identities, then update these copies in the same development change so the governance contract, protocol, evidence report, and roadmap do not drift.

## Current checkpoint

- SCAN Engine: v0.20
- Project documentation: v0.28
- Status: production-hardened pre-v1
- PR5 NotepadNext calibration: acquisition pass; cold scan not passed pending authentic v0.20 execution artifacts
- PR7 reconstruction proof: partial; M5 and M6A mechanisms pass, external-agent M6B remains open
- H-001 blind holdout: frozen and source-uninspected

## Documents

- [`ANCHOR_CODING_PROMPT.md`](ANCHOR_CODING_PROMPT.md) — governing A1-A8 architecture and evidence contract.
- [`SCAN_PROTOCOL.md`](SCAN_PROTOCOL.md) — operational scanning, certification, promotion, and reconstruction protocol.
- [`SCAN_REPORT.md`](SCAN_REPORT.md) — executed evidence, specimen findings, calibration history, and honest coverage state.
- [`SCAN_CREATION_PLAN.md`](SCAN_CREATION_PLAN.md) — engineering roadmap and PR1-PR8 certification ledger.
- [`evidence/pr5/PR5_ACQUISITION_RECEIPT.md`](evidence/pr5/PR5_ACQUISITION_RECEIPT.md) — exact pinned-source acquisition and archive digest evidence.

## Synchronization rules

1. Update the Drive documents in place; do not replace them with newly created files.
2. Mirror the same document bytes into this directory as part of the corresponding implementation or release change.
3. Keep aspirations in the creation plan and executed evidence in the report.
4. Do not promote `UNKNOWN`, `PARTIAL`, or `BLOCKED` findings into completed claims.
5. Do not alter A1-A8 merely to describe an implementation change.
6. Record only tests, scans, calibrations, and certifications that were actually executed.
