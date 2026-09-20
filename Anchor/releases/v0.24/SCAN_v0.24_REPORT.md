# SCAN Engine v0.24 Release Report

Release status: **FROZEN FOR PR5 BOUNDED-AST CALIBRATION**

Engine version: `0.24.0`

Specimen target: `dail8859/NotepadNext@f57db52d6760a2ce4149a37190c3adaa586845f5`

Tree: `f0995b128bf6dbc73e5d0f3ef4e4f302f8a3081b`

## Purpose

v0.24 is a generic PR1/PR2 correction admitted by the sealed v0.23 calibration. It bounds Clang stdout in memory, stops oversized compiler output, and retries oversized or timed-out full AST attempts with one mechanically derived declaration filter. Filtered AST evidence remains explicitly PARTIAL and conservative C++/Qt fallback extraction continues.

The release also removes three real projection-determinism hazards discovered by two full clean scans: process-local Clang declaration pointers no longer enter persisted IDs or attributes; bounded recovery records configured limits and outcomes rather than a scheduler-dependent timeout-versus-byte race; and case-equivalent capability tokens use a total lexical order.

## Safety and determinism

- Clang is invoked directly with a read-only, whitelisted parse context; specimen build scripts, response files, plugins, generated commands, and linker steps are not executed.
- Compiler time remains limited to five seconds per translation unit.
- Retained JSON AST output remains limited to 64,000,000 bytes per translation unit.
- Filter selection is derived only from the current source filename and mechanically recognized declarations.
- Process-local Clang IDs are used only inside one AST resolution pass.
- Two full fresh scans of all 1,928 files produced identical canonical projections and zero canonical-table row differences.

## Frozen artifacts

| Artifact | Bytes | SHA-256 | Reproducibility |
|---|---:|---|---|
| `SCAN_ENGINE_v0.24.zip` | 201,256 | `92c1ff83a13c1a940fb9d608451e9bfb56645368e405ee4ee790f2ad2c39cc15` | second independent build byte-identical |
| `scan_software_body-0.24.0-py3-none-any.whl` | 126,150 | `f6b0a2cf8b79a89ab7c6a06dbf1d141a56862a1037fba941088a0c8b8c645735` | second fixed-epoch build byte-identical |

The source package contains 68 manifest-tracked files plus `PACKAGE_MANIFEST.json`, with zero bytecode files. Package-manifest SHA-256: `3d7560928dc7ffbaa5ce42aac86c8aea6ddcd5ba0a25d63b24e76b72c6511e47`.

## Qualification

- development suite: 128 tests PASS, 3 Windows privilege-dependent symlink tests skipped;
- clean extracted ZIP suite: 128 tests PASS, same 3 skips;
- clean extracted package audit: 68/68 PASS, zero issues;
- fresh Python 3.13.13 wheel installation: PASS, runtime version `0.24.0`;
- LLM-disabled release qualification: 12/12 required queries PASS, integrity `MAPPED`, zero integrity errors;
- two fresh full NotepadNext scans: all ten canonical projections byte-identical and zero canonical-table row differences;
- separate cache proof: 4,165 hits, zero misses, cache-independent projections byte-identical.

## PR5 compiler result

| Measure | v0.23 | v0.24 |
|---|---:|---:|
| Complete compiler ASTs | 83 | 84 |
| Partial/recovered compiler ASTs | 74 | 294 |
| Explicit unavailable/bounded units | 237 | 16 |
| Valid compiler evidence | 157 / 394 | 378 / 394 |
| Parser gaps | 311 | 310 |

The 16 remaining unavailable compiler units are vendored/test translation units. All application translation units now have compiler AST evidence, although filtered or diagnostically incomplete results remain PARTIAL.

## Sealed calibration

The exact frozen wheel/package completed the LLM-disabled, manifest-backed NotepadNext certification. The 276,698,801-byte bundle has SHA-256 `53d6aa30a2c24272bc1b5288348a194d4430d964cb432eaf4ebab6eb2d50c972`. Independent verification passed 12/12 manifest files, projection verification, and zero issues.

The certified graph contains 124,255 nodes, 139,536 edges, 136,818 evidence records, 407,458 semantic objects, and 1,013,513 semantic relations. Integrity remains PARTIAL only because of 13 known warning-level orphan-evidence records; there are zero integrity errors. Human-surface closure remains 347 bound, 59 partial, and 82 unresolved of 488. Effect closure remains 112 closed, 294 partial, and 82 unresolved.

Therefore the gate remains **PR5 CALIBRATION PARTIAL**. v0.24 advances bounded compiler evidence and release determinism. It does not complete semantic convergence, external-agent reconstruction, the untouched H-001 blind holdout, or production certification.
