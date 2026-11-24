# ADR 0010 — Vector hit payload round-trip

- Status: Accepted
- Date: 2026-11-25
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

The integration pass stopped at `512be58` with a genuine seam, recorded in
`eval/reports/INTEGRATION-BLOCKER.md`. Lane D's Qdrant adapter stores
operational fields in the Qdrant payload for filter pushdown; Lane E's
retrieval pipeline reconstructs `Chunk` from `VectorHit.payload` with the
frozen schema's `extra="forbid"`. `Chunk.model_validate(hit.payload)` therefore
raises `extra_forbidden` for exactly nine fields: `last_crawled_ts`,
`department`, `course_code`, `year`, `term`, `is_live`, `indexed_at`,
`deleted_at` and `superseded_by`.

Both lanes behaved correctly inside an underspecified port: `VectorHit.payload`
was described as "the stored Chunk dump" without saying whether "stored" meant
the raw storage record or the domain datum handed back across the port (L3).
The blocker note is the motivating evidence for this decision; no metric was
faked and no lane code was edited while the pass was parked.

## Decision

**Invariant.** Every payload returned through the `VectorStore` port must
validate losslessly as a `Chunk`:

```
for hit in store.search(...):
    Chunk.model_validate(hit.payload)
    assert hit.payload == Chunk.model_validate(hit.payload).model_dump(mode="json")
```

`VectorHit.payload` is the domain `Chunk` dump at the port boundary. Storage
may hold more than the domain model; that extra state does not cross the port.
This is a contract tightening on the port (L3), not a change to the `Chunk`
schema.

**Chosen resolution: 2 — domain-clean payloads.** Lane D's adapter strips the
nine operational fields from `build_payload`'s output before constructing each
returned `VectorHit`; it keeps them in the stored payload and its filter
indexes, where `is_live`, `last_crawled_ts` and the derived axes are needed for
query pushdown. No core schema field is added, so `AGENT.md` §3 (L6) is
unchanged and merged lane code still compiles (L14).

Evidence that no consumer needs these fields as first-class domain data:

- Lane F's freshness axis reads `chunk.last_crawled`, an already-declared L6
  field — not `indexed_at` or `is_live`
  (`packages/eval/src/uni_rag_eval/runner/harness.py`, `_freshness`).
- Lane D's `deleted_at` / `superseded_by` / `is_live` values are soft-delete
  filter predicates used inside the indexing adapter; document-level soft-delete
  reporting is parked on the board, and no consumer outside `packages/indexing`
  reads them back.
- `department`, `course_code`, `year` and `term` are query-time filter axes
  supplied by callers; they are not fields consumers expect on a retrieved
  `Chunk`.

**Contract assert.** `tests/contracts/port_contracts.py` gains
`assert_vector_payload_roundtrip_contract(store)`. It asserts not only that
`Chunk.model_validate(hit.payload)` succeeds but that the decoded `Chunk`
equals the one upserted — "losslessly" includes keeping declared fields such
as `Chunk.metadata` (ADR 0007). The helper is wired into the canonical fake
suite (`test_core_fakes.py`) and is the check Lane D's adapter must call on
the integration re-run. `tests/contracts/test_vector_payload_roundtrip.py`
pins the fake's reproduction of the blocker: it builds the exact enriched
payload, proves that payload raises `extra_forbidden`, and proves the
boundary-stripped hit validates. The collision is therefore exercised
deterministically (L4) rather than approximated away.

## Alternatives rejected

- **1 — declare the operational fields optional on `Chunk`.** Legal, but it
  admits storage state into the domain schema and would require an L6 wording
  change in `AGENT.md` §3. No downstream consumer reads the fields back, so the
  justification ADR 0007 requires for first-class fields is absent (L1).
- **3 — fold the fields into `Chunk.metadata`.** Keeps them visible, but
  `metadata` is `Mapping[str, str]` (ADR 0007): `deleted_at`/`superseded_by`
  are `None` and `last_crawled_ts` is a float, so the mapping needs lossy
  stringification or selective omission. It would also move storage state into
  the producer-notes field with no consumer to read it — a permanent seam for
  nobody.

## Consequences

- Lane D must apply the boundary strip and keep every declared `Chunk` field
  (including `metadata`, which `build_payload` currently omits) in the returned
  payload. The one-line fix request is routed to Lane D in the handoff; this
  change does not edit `packages/indexing` (L14).
- This ADR supplies the invariant and the reusable check, not the adapter fix.
  Blocker `512be58` stays STOPPED until Lane D applies the boundary strip,
  the integration branch is rebased and re-run with the populated store, and
  the first numbers table is published (see handoff).
- Migration: none for schema or stored data. Qdrant points keep their
  operational fields and filter indexes; only the returned payload shape
  changes. Lane E's reconstruction needs no change.
- The invariant is pinned by the shared suite, so any adapter that adopts
  `assert_vector_payload_roundtrip_contract` fails at contract time rather
  than during integration (L12).
