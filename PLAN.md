# MantleOS 2 Implementation Plan

This file is the project compass for completing MantleOS 2. Work should return
to this plan whenever discussion or experimentation moves away from the agreed
goal.

## Goal

Build a substrate-neutral MantleOS 2 framework on GitHub, use it to fully
assimilate a fresh Hermes checkout locally through direct source-code nerves,
verify that Hermes retains its native behavior, and publish the reproducible
Hermes delta seed as the first complete example.

MantleOS is an autonomic nervous system. It is not a plugin framework and is
not defined by Python or Hermes. The assimilator maps and understands a Body,
identifies its semantic seams and capabilities, inserts reversible nerves, and
connects those nerves to Mantle organs. Hermes is the first complete reference
Body; a second, materially different Body must later prove substrate
independence before the stable release.

## Governing decisions

- Direct user clarifications override documents. Otherwise, newer compatible
  evidence has priority. Genuine conflicts stop at a recorded user-decision
  gate.
- Layer 0 and the Default Body are the NEST. A corresponding Layer 0 VCW layer
  records semantic state and use.
- Committed VCW history is append-only. Full physical layers extend into new
  segments using the same Book. New tissue may be added to the organism, and
  reversible nerve lines may be inserted into Body source code.
- The Body remains behaviorally usable without Mantle, without a MIND, during
  stasis, and when the resident Heart is stopped.
- There is no Brain organ. A MIND call is one optional part of a full
  Heartbeat.
- The Heart is constructed first when practical. Preparation occurs before
  the first Heartbeat; the first successful full Heartbeat is birth.
- The Primer is the exact versioned Commandments plus a unique Personality.
  The Personality is generated from the mapped Body, observed behavior,
  documentation, declared purpose, and user-approved context. Previous
  personalities are examples, never generic templates.
- The Primer is always first in AppAI MIND context. Keys, credentials, and raw
  unrestricted private state never enter the MIND.
- Senses carry semantic observations inward. Limbs carry Body-authorized
  actions outward. A MIND proposes actions but cannot bypass Body authority.
- `COMMUNICATION.TXT` is the universal unencrypted two-way fallback. A saved
  user message causes a complete unscheduled Heartbeat.
- VCW semantic records have a portable contract and swappable carriers. The
  default carrier is an encrypted, hash-chained append-segment store.
- Development and CI use fresh disposable identities and VCWs. Failed or old
  test organisms are never restored, merged, or treated as ancestors.
- The already-born alpha Compiler will not be migrated into the completed
  implementation. A clean successor requires its own reviewed Primer and new
  explicit birth approval.

## Implementation sequence

### 1. Correct the public architecture

- Preserve `v2.0.0-alpha.1` as historical evidence and mark its plugin-style
  Hermes attachment as superseded.
- Remove plugin manifests, plugin registration, plugin activation, and plugin
  terminology from current code, tests, manifests, and documentation.
- Maintain a Keep / Adapt / Reject / Experimental donor ledger.
- Split the monolithic runtime into explicit Body, SELF, Heart, VCW, Book,
  Senses, Nerves, Limbs, Immune, physiology, MIND-boundary, and communication
  responsibilities without breaking the working CLI.

### 2. Build the generic assimilation pipeline

- Accept GitHub repositories, local directories, and supported artifacts.
- Acquire and fingerprint the source without executing it.
- Produce versioned Body Map, Seam Map, capability, behavior-baseline, and
  uncertainty records.
- Use language-aware analysis plus a developmental MIND to propose direct
  innervation. Candidate output remains quarantined.
- Insert minimal guarded nerve calls in a controlled destination. Every source
  insertion must have a semantic purpose, syntax-aware anchor, before/after
  hash, test, and reversible patch.
- Require an explicit sandbox gate before executing an unfamiliar Body's
  build or tests.
- Stop safely on unknown substrates or unresolved conflicts.

### 3. Complete organism physiology

- Implement canonical Books and explicit `Thought -> Book -> Memory` routing.
- Implement append extension, authenticated encryption, hash chains, atomic
  Heartbeat commits, reconstruction receipts, corruption detection, and
  concurrency protection without state-backup restoration.
- Implement construction, prebirth, birth, active, stasis, defense, starved,
  and recovery states.
- Implement capability discovery, quarantine, grants, ActionFrames, Limbs,
  verification, revocation, and safe receipts.
- Implement a NEST-contained, non-admin resident Heart installed only through
  explicit authorization.
- Monitor semantic commits rather than raw keystrokes.
- Recognize the narrow Food format, verify a provider with a bounded request,
  encrypt accepted provider state, consume the plaintext on success, and leave
  only a non-secret receipt.

### 4. Assimilate Hermes through direct nerves

- Start every run from a clean current Hermes clone and pin the exact upstream
  commit only after verification.
- Map session, submitted-user-turn, native LLM, tool authorization/completion,
  error, gateway, terminal, and shutdown seams.
- Insert guarded afferent and efferent nerves directly at those seams. Do not
  use Hermes plugin discovery or registration.
- Preserve ordinary Hermes interaction. `/mantle`, `mantle speak`, and
  `COMMUNICATION.TXT` explicitly address The Compiler.
- Reuse Hermes provider and tool capabilities only through the Mantle MIND and
  authority boundaries.
- Generate and validate a fresh unique Compiler Personality. Obtain user
  approval of the Primer before requesting a separate birth approval.
- Build the final local Compiler in a clean NEST with no copied alpha identity,
  key, Primer, or VCW.

### 5. Publish the reproducible delta and stable evidence

- Keep the Hermes seed in repository-readable form: upstream lock, Body Map,
  Seam Map, direct nerve patch, Mantle tissue, checksums, behavior gates,
  reconstruction receipts, and apply/verify/reverse commands.
- Prove that the seed reconstructs the certified prebirth tree byte-for-byte
  and reverses to the pristine upstream tree.
- Run native Hermes regression and smoke tests with Mantle absent, unborn,
  born without MIND, in stasis, with the Heart stopped, and in explicit AppAI
  mode.
- Test Windows and Linux on Python 3.11-3.13; run corruption, crash,
  concurrency, wrong-key, redaction, communication, authority, delta, and
  provider-boundary gates.
- Keep live OpenRouter tests manual, environment-protected, tightly bounded,
  and disposable.
- Release `alpha.2` after architectural correction, `beta.1` after complete
  Hermes certification, `rc.1` after the user selects and certifies a second
  Body, and `v2.0.0` after all core gates pass.

## Stable completion gate

MantleOS 2 is complete only when the public repository implements a generic
autonomic nervous system, two materially different Bodies pass the same
conformance contract, a fresh local Compiler completes reviewed birth and
communication, native Hermes behavior remains intact, and the public Hermes
delta can reconstruct and reverse the integration without vendoring Hermes or
publishing private organism state.

Migration, Engrams, rebirth, universal SPORE transport, autonomous post-birth
tissue adoption, and multi-Body motor arbitration remain visible experimental
tracks. They must not be claimed as certified or activated accidentally.
