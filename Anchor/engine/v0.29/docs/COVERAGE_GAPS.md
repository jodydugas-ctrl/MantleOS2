# SCAN v0.29 Coverage and Gaps Projection

## Purpose

The coverage/gaps projection makes existing SCAN uncertainty operationally visible without creating a new source of truth.

It is deliberately a **projection**, not a classifier.

Canonical coverage remains stored in `scan_index.sqlite` and in the existing mechanical closure state derived from that database. The projection may count, group, explain, and point back to those records. It may not change them.

## Outputs

### coverage_report.json

Machine-readable complete view containing:

- coverage-state counts by canonical layer;
- evidence-class and extractor counts;
- acquisition-state counts;
- existing surface/effect closure summaries;
- complete unresolved gap records;
- canonical IDs and evidence IDs needed to trace each gap.

### coverage_report.md

Compact human/agent summary. It intentionally avoids a single percentage because MAPPED, PARTIAL, BLOCKED, UNKNOWN, and NOT_APPLICABLE do not form one honest probability scale.

### gaps.md

Checklist of unresolved projected records grouped by cause/category. Each entry retains:

- current evidence state;
- canonical source ID;
- path when available;
- existing supporting evidence IDs;
- deterministic explanation;
- the kind of additional evidence that could resolve the gap.

The guidance is not proof and cannot itself promote a claim.

## Gap categories

The first schema recognizes:

- acquisition;
- parser;
- resource-limit;
- coverage-finding;
- mechanical-object;
- mechanical-relation;
- semantic-object;
- semantic-relation;
- completeness-dimension;
- surface-binding;
- effect-closure.

Categories are views over existing canonical records. They are not additional evidence states.

## Invariants

1. `scan_index.sqlite` remains authoritative.
2. Projection generation opens the database read-only.
3. No projection field can change canonical state.
4. No scalar confidence score is emitted.
5. All list ordering is deterministic.
6. Every unresolved checklist entry carries a canonical source ID.
7. Existing closure calculations are reused rather than reimplemented.
8. The files are included in `projection_manifest.json` so stale or altered copies are detectable.
9. Overlay/reconstruction promotion refresh paths regenerate the projection because those are legitimate canonical-state changes.
10. Deleting all three projection files loses no canonical evidence; they are reproducible from the DB.

## Why this precedes the uncertainty challenger

A challenger needs a precise, deterministic queue of uncertainty to interrogate. v0.29 first establishes that queue without introducing any AI authority. A later challenger may consume these records and propose targeted evidence searches, but it must not be allowed to edit their states directly.
