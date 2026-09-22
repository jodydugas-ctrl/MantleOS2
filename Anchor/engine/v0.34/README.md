# SCAN Engine v0.34

Status: **broader-calibration candidate — no scanner feature changes**.

v0.34 is stacked on the v0.33 parity/distribution candidate. This stage changes the test and qualification envelope rather than adding scanner behavior.

## Calibration objective

The production-readiness mechanisms added in v0.29-v0.33 must transfer across different software shapes and failure modes without specimen-specific rules.

The matrix combines frozen real repositories with deterministic adversarial fixtures.

### Frozen real repositories

- **NotepadNext** — Qt/C++ desktop application.
- **Moji** — TypeScript/Electron application.
- **pell** — plain JavaScript/web editor.

Every external specimen is pinned to an exact commit and tree identity.

### Deterministic adversarial fixtures

- unsupported Python CLI;
- mixed-language C++/HTML/TypeScript/Python specimen;
- metadata-only/incomplete acquisition manifest;
- ambiguous static web routing;
- forced resource-budget interruption.

These fixtures are deliberately small. They test epistemic behavior and failure handling, not application-specific extraction quality.

## Calibration invariants

For every applicable specimen the gate checks:

- duplicate cold-scan determinism;
- zero integrity ERRORs;
- coverage/gaps generation;
- uncertainty-challenger consistency;
- triage ranking consistency;
- layered-provenance object reconciliation;
- Blueprint/conformance-manifest generation;
- parity scenarios equal the MAPPED+REQUIRED contract set;
- portable parity regeneration.

Failure-mode fixtures additionally require:

- unsupported CLI content does not invent actionable human surfaces;
- incomplete acquisition remains explicit and challengeable as external input;
- ambiguous routing preserves uncertainty rather than manufacturing a required handler contract;
- resource-budget stops remain explicit coverage gaps rather than silent omission.

## Anti-overfitting rule

The calibration workflow does not assert hand-tuned node/surface counts for new specimens. It asserts structural invariants and records observed metrics.

No scanner rule may inspect specimen names, repository names, or calibration IDs to satisfy this gate.

## Explicit non-goals

This stage does not add:

- new adapters;
- new extraction rules;
- new evidence-promotion rules;
- runtime execution;
- reconstruction scoring changes;
- calibration-specific exceptions.

The next roadmap stage is independent reconstruction proof.

v0.28.0 remains the latest released version while stacked production-readiness candidates are evaluated.
