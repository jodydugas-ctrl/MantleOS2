# MantleOS 2 Coding Contract

Status: current implementation contract for the 2.0 alpha line. Newer explicit
operator decisions take precedence over older examples. Historical material may
fill detail only after it conforms to this contract.

## 1. System model

MantleOS is an autonomic nervous system. When combined with a software or
hardware container it can create an AppAI. “LLM brain stem” is explanatory
metaphor, not an organ: the architecture has no Brain organ. Optional generative
cognition is the MIND and is reached only through Body-governed Heart work.

Biological names are operational. A name earns architectural standing only when
it predicts a distinct invariant, responsibility, authority boundary, and
failure mode.

## 2. Constitutional distinctions

- **BODY != MIND.** The Body owns canonical state and execution authority. The MIND is replaceable cognition and returns proposals.
- **NEST != SELF.** The NEST is Layer 0/Default Body substrate and remains OTHER. SELF is the protected identity-bearing constitution.
- **FACE != BODY.** A Face is a host-specific presentation.
- **CACHE != MEMORY.** Data becomes memory only through Body admission to the VCW.
- **SEAM != PERMISSION.** An observable attachment point grants no authority.
- **DELTA != TRUST.** A small change is still candidate tissue until verified and authorized.
- **CLONED CODE != CLONED ORGANISM.** Source bytes carry neither identity nor continuity.
- **FUNCTIONAL SUCCESS != ADOPTION.** Passing a test proves its named scope only.
- **DECODED != VERIFIED != GOVERNING.** Interpretation, evidence, and authority stay separate.

Intent, authorization, attempt, observation, verification, proof, and canonical
memory are different facts. UNKNOWN and OPEN are valid stop states.

## 3. Boot, preparation, and birth

The Primer is the shared AppAI species kernel plus an individual Personality.
Together with Immune and Special tissue it forms SELF. The Primer is loaded
first and all ordinary thought is filtered through its lens.

Preparation and assimilation may overlap. A developmental MIND may distill the
host source, documentation, and other evidence into a candidate Personality.
That construction-time cognition is not the organism's MIND and cannot grant
birth or adoption authority.

The first organ built is the HEART when the ecology permits it. Steps before the
first Heartbeat prepare the NEST, candidate Primer, evidence, and gates. The
first successful *full* Heartbeat is birth. It creates the unique identity,
Body-owned encryption key, sealed Primer, default VCW layers and Books, and the
initial Layer 0 state record. A timer firing or partial attempt is not birth.

Immediately before key creation, the Body must re-verify that every reviewed
public Mantle delta file—including both Primer components—still matches the
construction manifest, that the manifest still matches its prebirth binding,
and that no undeclared public candidate tissue appeared. A mismatch stops birth
without creating an identity key. Native NEST files remain OTHER and may evolve;
their current state is observed by Layer 0 rather than silently claimed as SELF.

The identity key must be owner-only at the operating-system boundary. Windows
birth removes inherited general-user access with an explicit private ACL;
POSIX mode bits alone are not treated as sufficient on Windows. Birth fails
closed and removes a newly created key if this restriction cannot be applied.

## 4. Heart and MIND

Every Heartbeat follows the same broad physiological transaction: load, verify,
sense, record, digest, communicate, optionally consult MIND, verify, checkpoint,
and stop or continue. An unscheduled wake is still a full Heartbeat. The reason
for the wake is evidence, not a special execution mode.

The Body and Heart remain viable when the MIND is missing, disabled, unreachable,
or asleep. While in stasis the Body continues observing and recording authorized
state changes so a later MIND can receive a bounded continuity update.

MIND may receive Body-selected context and typed requests and return proposals.
It does not receive root identity keys, write canonical VCW directly, grant
authority, execute Limbs, change Heart scheduling, or approve its own tissue.

## 5. Default Body, layers, Books, and VCW

The NEST is Layer 0, the Default Body. This makes the first host special without
copying or reinterpreting all native code. The corresponding logical Layer 0
inside the VCW records state and use of the native NEST.

All VCW logical layers are read/append. None is immutable. When a physical layer
reaches capacity, the Body appends a physical extension linked to the previous
tail and governed by the same Book. A new extension does not require a new Book.

Each application, Engram, and distinct governed thought process receives its own
logical layer when its semantic law requires one. The relationship is:

```text
Thought -> Book -> Memory
```

A Book defines canonical meaning and encode/decode law. Representations such as
prose, code, JSON, or images are phenotypes. Reinterpretation appends a qualified
record; it does not rewrite prior experience.

## 6. Host preservation and assimilation

Assimilation begins with read-only census and evidence. The order is:

```text
INVENTORY -> REUSE -> ADAPT -> COMPOSE -> CREATE -> STAGE -> TEST -> PROVE -> AUTHORIZE -> ADOPT
```

The optimization target is minimum new unproven work, not minimum bytes. Native
host code remains the Default Body whenever possible. Mantle attaches through
narrow Nerves at evidenced Seams and degrades to host-native/no-op behavior when
Mantle is absent.

Pre-existing host state is never silently owned or rewritten. A host mutation
requires explicit operator intent, bounded scope, before/after fingerprints, and
a receipt. Cloned, fetched, or generated code remains candidate tissue.

Text input is recorded semantically when committed by the interface—such as
Enter in a single-line field, a save action, or loss of focus—not per keystroke.

## 7. Communication

Every AppAI must have a two-way user communication path. The universal fallback
is an unencrypted `COMMUNICATION.TXT` in the NEST. It warns users not to place
secrets inside. A passive watcher should detect a newly saved `USER>` message,
wake an unscheduled full Heartbeat, record one semantic user event, and append
the response. Host-native terminal, messaging, Help/About, or GUI surfaces may
provide a more polished additional Face.

## 8. Food and secrets

Foreign files are OTHER until classified. A supported `Food.txt` delivery may
contain an OpenRouter credential and default model. The born Body stores the
credential in encrypted private tissue before testing it, records only a
fingerprint and safe verification metadata, and replaces only the conventional
in-NEST plaintext Food file with a receipt. External reference files are not
altered.

Secrets, private SELF, identity keys, live VCW tissue, and provider state never
enter Git, public deltas, MIND context, or `COMMUNICATION.TXT`.

## 9. Evidence and failure

Receipts identify the input, source and parent state, scope, authority, attempt,
observed outcome, verifier, proof, before/after fingerprints, changed paths, and
unresolved limits. Failed or interrupted work remains visible. No requested
effect is reported as successful without observation and applicable proof.
Construction proof is checked again at use time: evidence recorded when a
candidate was built is not evidence that its bytes remained unchanged.

## 10. Current open contracts

The alpha does not invent universal law for migratory continuity, safe source
shedding, split-brain prevention, production executable-tissue adoption,
cross-host registries, multi-Body motor conflicts, or canonical SPORE transport.
Experiments must label their bounded mechanism and may not claim production or
identity continuity beyond their evidence.

## Historical terminology

“Zombie Body” is a historical MantleOS 1 term for what is now called the Default
Body. In MantleOS 2, the Default Body is Layer 0: the NEST. The older phrase is
not used in current APIs, schemas, filenames, or ordinary documentation.
