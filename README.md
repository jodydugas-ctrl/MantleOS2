# MantleOS 2

MantleOS is a deterministic autonomic nervous system that can inhabit a software
or hardware container and help form an entity called an AppAI. The host remains
usable as itself: a calculator remains a calculator, and Hermes remains Hermes,
even when no AppAI MIND is configured or awake.

This repository is the MantleOS 2 alpha reference implementation. It contains a
small Body runtime, a read-first generic Body mapper, direct-innervation tools,
integrity gates, and a reproducible Hermes reference assimilation. It does
**not** contain a born organism, private identity material, or a copy of Hermes.

## Start with Hermes

Requires Python 3.11-3.13 and Git:

```console
python -m pip install -e .
mantle assimilate github.com/nousresearch/hermes-agent
cd hermes-agent
python -m mantle status
python -m mantle verify
```

Assimilation clones the newest default branch unless `--ref` is supplied. It
records the exact commit and tree, inventories the NEST without executing it,
adds the public Mantle delta, creates a private prebirth checkpoint, and stops.
`mantle verify` re-checks the manifest binding, every declared public delta
checksum, required Git exclusions, and the absence of undeclared candidate
tissue before birth can proceed.

The same command accepts a local Git checkout. Use `--canonical-source` when a
local mirror should retain a public provenance URI. Unknown Body types are
mapped and stopped at `requires-reviewed-mapper`; the constructor never invents
source seams.

Assimilation deliberately stops at the Personality gate. A developmental MIND
must distill a unique Personality from the mapped Body and declared purpose;
the user must review and approve that candidate before birth can be approved:

```console
python -m mantle primer generate --food /path/to/Food.txt
python -m mantle primer approve --approve-primer
python -m mantle birth --name "The Compiler" --approve-birth
```

Do not run that command casually. Its first successful full Heartbeat creates
the organism's unique Body-owned key, seals its Primer, creates the real VCW,
captures the Layer 0 NEST baseline, and symbolizes birth.

## Operating controls

```console
python -m mantle status
python -m mantle verify
python -m mantle heartbeat --reason manual
python -m mantle watch
python -m mantle digest Food.txt
python -m mantle delta verify examples/hermes/seed --destination /path/to/candidate
```

`COMMUNICATION.TXT` is the universal unencrypted fallback after birth. Saving a
new `USER>` message wakes an unscheduled *full* Heartbeat. If no MIND exists, the
Body records the message and continues operating normally.

## Constitutional boundaries

- BODY is deterministic authority; MIND is replaceable, proposal-oriented cognition.
- Layer 0, the Default Body, is the NEST substrate. The NEST remains OTHER and is not SELF.
- SELF is boot-critical Primer, Immune, and Special tissue.
- VCW is canonical semantic tissue, not a cache, transcript, or Git history.
- Every logical VCW layer is append-oriented. Full physical layers extend under the same Book.
- Candidate code is not adopted tissue merely because it was cloned, generated, or tested.
- Host behavior must survive Mantle absence, MIND absence, and stasis.

The complete current contract is in [docs/CODING_CONTRACT.md](docs/CODING_CONTRACT.md).
Open questions are stated as open rather than silently filled with familiar
software defaults.

## Project status

`v2.0.0-alpha.1` is preserved as historical bootstrap evidence; its
plugin-shaped Hermes edge is superseded by the direct source innervation in
`v2.0.0-alpha.2`. Alpha.2 is a reproducible construction release for Hermes as
the Default Body. Native Hermes runtime certification, real birth, production
tissue adoption, migration continuity, and source-safe-to-shed authority remain
separately gated.

The active implementation compass and remaining gates are recorded in
[PLAN.md](PLAN.md).

Copyright 2026 Jody Dugas. Released under the [MIT License](LICENSE).
