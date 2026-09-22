# SCAN v1.0.0

SCAN v1.0.0 completes the production-readiness path built on the frozen v0.28
release without changing the evidence-first authority model.

## Production-readiness path

The release carries the staged work through:

- deterministic coverage and unresolved gaps;
- an uncertainty challenger that proposes rechecks without promoting evidence;
- transparent investigation triage ranking;
- layered provenance from source evidence through presentation;
- portable parity scenarios and agent-distribution metadata;
- broader calibration across supported, unsupported, mixed, incomplete,
  ambiguous, and resource-limited specimens;
- independent source-blind reconstruction proof infrastructure;
- explicitly plan-hash-authorized runtime validation;
- operational hardening for malformed input, resource ceilings, derived-state
  recovery, and concurrent output writers;
- final exact-byte v1.0 certification.

## Final release gates

The v1.0 publication workflow requires all of the following on the release
commit before the tag is created:

- complete inherited regression suite;
- Linux, macOS, and Windows focused certification lanes on Python 3.11, 3.12,
  and 3.13;
- LLM-disabled local package qualification and sealed package certification;
- independent-reconstruction regression evidence;
- real authorized runtime validation under Linux network-namespace denial;
- wrong-plan-hash refusal before execution;
- source immutability and secret non-forwarding during runtime validation;
- operational-hardening regressions;
- clean wheel build, fresh installation, and installed-CLI scan;
- deterministic source ZIP;
- aggregate CI certificate and manifest.

## Authority boundary

A v1.0 PASS applies to the exact commit and package bytes named by the
certificate. It does not imply universal semantic completeness, universal
runtime or pixel equivalence, hostile-code sandbox security, distributed
locking, exhaustive parser fuzzing, or a production performance SLA.

PR5 NotepadNext calibration remains PARTIAL wherever its preserved evidence is
PARTIAL, BLOCKED, or UNKNOWN. Release certification does not erase specimen
uncertainty.

## Published assets

The release publishes:

- the Python wheel;
- a deterministic source ZIP;
- `PACKAGE_MANIFEST.json`;
- `V1_RELEASE_MANIFEST.json` and `v1_local_release_certificate.json` from the sealed local package certification;
- `release_qualification.json`;
- `runtime_validation.json` from the authorized live-runtime gate;
- `V1_CI_RELEASE_CERTIFICATE.json`;
- `V1_CI_MANIFEST.json`;
- `integration_stage_evidence.json`, binding the main merge tree to the successfully checked integration source head;
- `SHA256SUMS.txt`.

The tag is created only from a successful final certification run on `main`.
The publication step refuses to move an existing `v1.0.0` tag to different
bytes.
