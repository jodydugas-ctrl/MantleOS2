# Resident Heart lifecycle evidence

Scope: issue #16, incremental progress after PRs #30 and #31. This document
records actual boundaries, not complete native service certification.

## Runtime and scheduling

The generated runner imports the NEST-local `mantle/runtime/mantleos` organs
using isolated Python. A global constructor installation is not its organ source.
Python and cryptography remain runtime prerequisites.

`MantleBody.watch` runs a full startup Heartbeat, observes committed communication
at the configured file cadence and runs scheduled full Heartbeats at the separate
maintenance cadence. Both intervals must be positive and finite. Idle waits are
at most 100 ms, with stop checked again after waiting and before a new Heartbeat.
Short stop-check slices do not increase the configured file-observation rate.

When maintenance and a file change coincide, a single `resident-scheduled`
Heartbeat runs all ordinary phases, including communication. A stat failure
during save/replace or temporary absence does not skip the maintenance decision.
An actual failed Heartbeat still fails visibly; this is not permission to ignore
storage failures. Post-Heartbeat observation includes the response written by
that beat so the response alone does not produce another wake.

This polling change does not claim durable concurrent-editor delivery, stable
message IDs, lossless saves or atomic transcript/VCW publication. Those remain
separate communication/storage gates.

## Cooperative command-line shutdown

`resident.watch_with_signals` owns handlers only while the CLI `watch` command
runs on the main thread. Embedded hosts may continue using their own handlers
and the existing `stop_requested` callback instead.

- SIGINT and SIGTERM, plus SIGBREAK where available, set a single stop flag.
  The handler does not acquire locks, write state, raise into a transaction,
  contact a provider or start another Heartbeat.
- A started Heartbeat is allowed to finish; no new Heartbeat starts after the
  watcher observes stop. A failure during that beat propagates as failure.
- Prior handlers are restored on normal return, runtime failure and partial
  installation failure. A worker-thread call is refused before handler changes.
- A normal CLI return prints `status=stopped`, the first received signal name
  and `shutdown=cooperative-between-heartbeats`. That output is process evidence,
  not a new VCW lifecycle record, organism death or an atomic shutdown checkpoint.

The implementation follows Python's [main-thread signal model](https://docs.python.org/3.13/library/signal.html).
Signal delivery depends on the operating system and launch surface. In
particular, Windows process termination is a forced kill rather than a Python
SIGTERM callback. Do not infer graceful Windows Task Scheduler shutdown from
the cooperative handler tests.

Idle stop checks have a 100 ms maximum requested wait slice, not a real-time
scheduling guarantee. Synchronous disk/lock/provider work can delay return.
A hard shutdown deadline needs the planned bounded asynchronous work lifecycle
and durable disposition of unfinished attempts. This implementation neither
claims that guarantee nor installs anything to resist OS termination.

## Verification map

| Evidence | Proven scope | Not proven |
| --- | --- | --- |
| `test_watch_shutdown.py` with controlled clock/state | Pre-start/idle/in-flight stop ordering; failed beat remains failed; finite intervals; cadence; unavailable file; collision and response-echo behavior | Real OS scheduling, storage durability or provider cancellation |
| `test_resident.py` | Explicit installation gates, NEST-local runner, mocked Windows/Linux registration; signal-handler restoration and main-thread boundary | Actual Task Scheduler/systemd installation or console signal delivery |
| `test_resident_process.py` existing cross-platform process test | Real encrypted disposable VCW; startup, communication, forced stop/restart, pending host receipt recovery, unchanged Primer and native Body | Crash during admission, OS-managed automatic restart or fenced canonical writer |
| `test_real_sigterm_stops_idle_resident_without_extra_heartbeat` (Linux) | Real SIGTERM delivery, exit code zero with stop result, no extra VCW event/Heartbeat, preserved Primer/native bytes and usable native Body | Windows graceful stop; termination during provider I/O; native systemd service lifecycle |

These tests run in the existing Windows/Linux Python 3.11–3.13 matrix. The real
SIGTERM case is explicitly skipped on Windows instead of fabricating evidence.
Fixtures birth only disposable test organisms; no real Compiler SELF or creator
machine service registration is changed.

## Remaining acceptance gates

1. Native Task Scheduler and systemd installation/start, automatic restart,
   graceful stop, failed-registration recovery and safe removal in disposable
   platform environments, including exact registration ownership/path checks.
2. A single serialized Body mutation port and storage-enforced writer epochs;
   current process/file locks must not be described as stale-writer fencing.
3. Crash-atomic admission/root/receipt publication and durable unfinished-work
   dispositions before claiming complete Heartbeat transaction recovery.
4. Bounded asynchronous provider/effect cancellation, an overall shutdown deadline
   and explicit uncertainty for work that may have happened remotely.

Do not close issue #16 or promote full resident certification until its actual
platform and storage evidence exists. Real resident installation on the creator's
PC remains separately approved.
