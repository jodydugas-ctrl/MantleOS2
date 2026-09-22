# SCAN Engine v0.32

Status: **layered-provenance integration candidate — not release-qualified**.

v0.32 is stacked on the v0.31 triage-ranking candidate and implements only the fourth production-readiness stage: explicit provenance layers over the existing canonical semantic graph.

## Layer model

The canonical graph remains singular. v0.32 projects its objects into:

- **E0 — source/evidence:** specimen identity, files, direct evidence;
- **E1 — mechanical anatomy:** extracted anatomical objects, graph-relation claims, scanner findings;
- **E2 — semantic interpretation:** interpretations and behavior contracts;
- **E3 — reconstruction contract:** reconstruction anchors;
- **E4 — human description:** presentation-only prose/description objects.

E4 is deliberately non-canonical. Human-readable explanation may cite lower-layer IDs but cannot upgrade source evidence or mechanical claims.

## Output

Ordinary scans emit:

- `layered_provenance.json`
- `layered_provenance.md`

The projection can be regenerated from an existing canonical database:

```bash
scan-body provenance-layers .scan/scan_index.sqlite --out-dir ./provenance
```

Semantic-overlay ingestion and reconstruction promotion also refresh the layered projection so E2/E3 state cannot silently lag behind the canonical store.

## What is preserved

Each object retains its own coverage state. The projection does not derive one flat confidence value.

This means, for example:

- direct evidence can be `MAPPED`;
- the mechanical function/call relationship can be `MAPPED`;
- the behavioral interpretation can remain `PARTIAL`;
- the reconstruction anchor can remain `PARTIAL`;
- a human description can be readable while remaining presentation-only.

For each object the projection exposes:

- layer identity;
- original coverage state;
- immediate proof support;
- lower-layer support;
- evidence IDs reachable through typed proof relations;
- source-file IDs;
- contradiction relation IDs;
- whether a proof path reaches E0.

Unknown future object types are emitted as `UNCLASSIFIED`, never silently assigned to a layer.

## Authority boundary

- one canonical graph: `scan_index.sqlite`;
- no duplicate provenance database;
- no canonical writes from the projection;
- no confidence aggregation;
- no automatic promotion;
- higher-layer prose cannot alter lower-layer evidence.

## Explicit non-goals

This tranche does not add:

- parity/Gherkin scenarios;
- AGENTS.md distribution;
- calibration expansion;
- new runtime evidence;
- new reconstruction scoring;
- evidence promotion rules.

Those remain later roadmap stages.

## Promotion gates

Before this stage is admitted:

1. all inherited v0.31 tests remain green;
2. projection generation and regeneration are deterministic;
3. read-only regeneration leaves the canonical DB unchanged;
4. projected object IDs exactly reconcile with canonical semantic objects;
5. per-object coverage is unchanged by layer classification;
6. a synthetic E0→E4 chain proves independent coverage at each layer;
7. promoted semantic overlays refresh E2/E3 projections;
8. unclassified object types remain visible;
9. E4 remains explicitly presentation-only.

v0.28.0 remains the latest released SCAN version while the stacked production-readiness candidates are evaluated.
