# SCAN Engine v0.36

Status: **authorized-runtime-validation candidate — not release-qualified**.

v0.36 is stacked on the v0.35 independent-reconstruction-proof candidate and implements the eighth production-readiness stage: opt-in runtime validation where the operator has explicitly authorized execution.

Ordinary SCAN remains static, read-only, and non-executing.

## Runtime authorization model

Runtime execution is available only through:

```bash
scan-body runtime-validate <target_root> <plan.json> \
  --out <runtime_output> \
  --authorize-plan-sha256 <exact-plan-sha256>
```

The authorization hash must exactly match the bytes of the plan file presented for execution.

If the hash does not match, SCAN returns `BLOCKED / PLAN_NOT_AUTHORIZED` before network setup or target execution.

## Plan scope

The v0.36 runtime-plan schema is intentionally narrow:

`scan-runtime-validation-plan/0.1`

A plan supplies:

- a stable `plan_id`;
- an argv-style command array;
- a relative working directory;
- a bounded timeout;
- a bounded captured-output size;
- optional static contract/scenario source references;
- explicit runtime assertions.

Supported assertions:

- `EXIT_CODE_EQUALS`
- `STDOUT_CONTAINS`
- `STDERR_CONTAINS`
- `FILE_EXISTS`
- `FILE_SHA256_EQUALS`
- `JSON_POINTER_EQUALS`
- `DURATION_MS_MAX`

A structured observer or test harness can therefore emit JSON describing runtime state, persistence, dynamically created controls, extension loading, or other observations; SCAN asserts only the fields named in the authorized plan.

## Execution boundary

Authorized execution uses:

- a temporary copy of the target;
- shell disabled;
- stdin disabled;
- sanitized environment;
- no arbitrary environment forwarding beyond `PATH`;
- timeout enforcement;
- bounded recorded stdout/stderr;
- relative-path validation;
- symlink rejection;
- Linux network namespace isolation with loopback only;
- source-tree hash verification before/after execution.

v0.36 supports `network = DENY` only.

If the platform cannot mechanically establish the network-denied executor, validation returns `BLOCKED` and does not execute the target.

The Linux network namespace is an execution-isolation control for cooperative authorized validation, not a hostile-code security sandbox.

## Evidence semantics

Runtime output is emitted as:

- `runtime_validation.json`
- `runtime_validation.md`

The report records:

- exact authorized plan SHA-256;
- static/parity source references;
- network-isolation mechanism and observed namespace interfaces;
- source and workspace tree hashes;
- process return code and elapsed time;
- bounded stdout/stderr plus hashes;
- assertion-level PASS/FAIL observations;
- whether the original source tree remained unchanged.

Runtime evidence remains a sidecar observation layer.

It does not:

- write `scan_index.sqlite`;
- update static coverage;
- resolve a PARTIAL/UNKNOWN automatically;
- create a semantic overlay;
- promote reconstruction anchors;
- change ordinary SCAN behavior.

A runtime PASS means only that the assertions in that exact authorized plan were observed to pass during that execution.

## Qualification coverage

The v0.36 gate proves:

1. ordinary `scan-body scan` still never executes specimen code;
2. a wrong plan hash blocks before execution;
3. network modes other than DENY are rejected;
4. unsafe relative paths are rejected;
5. runtime execution occurs only in a temporary copy;
6. source bytes remain unchanged;
7. runner secrets are not forwarded to the target;
8. Linux runtime execution sees loopback only;
9. state-transition/persistence/dynamic-probe assertions can be witnessed mechanically;
10. timing can be observed without turning it into a static claim;
11. failed runtime assertions remain failed observations and do not promote static evidence.

## Explicit non-goals

This stage does not add:

- general network-enabled runtime execution;
- automatic GUI-driving logic;
- pixel/visual equivalence;
- automatic static-to-runtime promotion;
- hostile-code sandbox guarantees;
- new static adapters or extraction rules.

Those would require separate review and evidence.

The next roadmap stage is operational hardening.

v0.28.0 remains the latest released version while stacked production-readiness candidates are evaluated.
