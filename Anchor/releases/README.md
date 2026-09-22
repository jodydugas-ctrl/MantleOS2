# SCAN release and calibration index

## Current release line

SCAN v1.0.0 is the current production-readiness release line. Its source package
lives under [`../engine/v1.0/`](../engine/v1.0/README.md).

v1.0 release evidence is produced by the repository's final certification
workflow rather than by checking generated wheels or large certification bundles
into Git. The workflow binds one exact commit to:

- the exact package manifest;
- a sealed local package certification;
- the complete inherited regression suite;
- Linux, macOS, and Windows certification lanes across the supported Python range;
- live, explicitly authorized runtime validation under enforced network denial;
- operational-hardening regressions;
- a clean built wheel and deterministic source archive;
- an aggregate CI release certificate and manifest.

A source change or merge result requires a fresh final certification run before
that new revision inherits the v1.0 certified status.

## Historical frozen releases

`v0.21/` and `v0.22/` preserve small historical release reports and
sealed-calibration receipts/comparisons. `v0.23/` contains the first frozen
compiler-enabled package and calibration. `v0.25/` contains the combined
adaptive/bounded source ZIP, wheel, package-freeze and determinism receipts, and
final certification/calibration reports. `v0.26/` preserves the
surface-denominator-corrected scanner/calibration checkpoint. `v0.28/` is the
last frozen pre-v1 release lineage.

Mechanical certification PASS verifies an evidence handoff or release package;
it is not semantic convergence. PR5 NotepadNext calibration remains PARTIAL.
The immutable v0.20 cold pre-oracle baseline is indexed under
[`../evidence/pr5/`](../evidence/pr5/). Acquired NotepadNext bytes, oracle
materials, and large sealed specimen bundles are not published in this Git
directory. Their recorded digests remain the identity boundary for the private
artifacts.
