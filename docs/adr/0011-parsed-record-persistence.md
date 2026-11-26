# ADR 0011 — Parsed-record persistence

- Status: Accepted
- Date: 2026-11-26
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

G3 shipped `GET /api/v1/papers` as real-but-fixture-backed on both backends.
`FakePapersProvider` (`apps/api/src/uni_rag_api/service.py`) returns frozen
`PaperRecord`s from `apps/api/src/uni_rag_api/fixtures.py`: every item carries
`source_url`, `last_crawled`, `page` and an `image_ref` whose key exists in the
`ObjectStore`. The route's own description says so
(`apps/api/src/uni_rag_api/routers/papers.py:22-25`), as does
`apps/api/README.md:19-22`. No parsed-record store is consulted. `PaperRecord`
is API-local — `PastPaperQuestion` plus `last_crawled` behind the API-local
`PapersProvider` port (`apps/api/src/uni_rag_api/ports.py:38-66`); no core
schema or port change rode in (L3, L5).

Lane B already emits parsed past-paper questions with `ImageRef`s, but
`docs/PARKING_LOT.md` keeps "storing parsed records in Postgres/Qdrant" out of
scope pending an ADR (L1, lines 23 and 39). G3's handoff recommends promoting
persistence as the next ADR and records two dependent handoffs: the real papers
provider waits for it, and Lane H's migration `/api/papers` → `/api/v1/papers`
plus `last_crawled` in the strict mirror waits on the checkpoint. G4 and the H
migration are RED pending exactly this decision. This ADR resolves it; no lane
code is touched here.

## Decision

Promote parsed-record persistence into scope, with three bindings:

**What is persisted — the parsed `PaperRecord`.** Exactly the datum G3's fake
returns today: the ADR 0007 `PastPaperQuestion` finder fields (`course_code`,
`term`, `exam_type`, `department`, question text, page) plus frozen provenance —
`source_url`, `last_crawled: datetime`, `page` and an `image_ref` whose key is
resolvable in the `ObjectStore`. This is the parser's segmented output, not the
raw crawl response and not a `Chunk`: no enrichment, no embedding and no
operational filter state (ADR 0010). Provenance is stored with the record at
write time; it is never reconstructed at read time (L5).

**Where — Lane D's relational metadata store.** A dedicated parsed-record table
in Postgres through Lane D's domain-local `MetadataStore`
(`packages/indexing/src/uni_rag_indexing/domain/store_types.py`), with a new
Alembic revision under `infra/migrations/versions/`. Page images stay in
`ObjectStore` (MinIO); the stored `image_ref` key is the link, and no new core
port is added (L3). Qdrant remains vector-only: `Chunk` payloads and the nine
operational filter fields stay as ADR 0010 defines them, and parsed records are
not duplicated there. New store methods stay domain-local until a
CONTRACT-CHANGE PR is accepted by Lane 0 (L14); `AGENT.md` §3 (L6) and ADR 0007's
shared block vocabulary are unchanged.

**Rule — the papers provider goes real only post-persistence.** A real
`PapersProvider` may be wired into `apps/api` composition only once the
parsed-record store and migration exist and a contract check proves a persisted
record round-trips through `find()` with `source_url`, `last_crawled`, `page`
and a resolvable `image_ref` intact (L5, L12). Until then
`FakePapersProvider` is the only provider on both backends and the route's
"fixture-backed" OpenAPI wording remains truthful (L1, L4). G4 is the wiring
milestone and retires that wording when the real provider lands; persistence
is not a prerequisite for Lane H's client-side route/mirror migration.

## Alternatives

- **DEFER and wire a real provider against the live site or crawl response**
  — rejected: G3's frozen provenance can only come from a stored record; live
  reads break determinism (L1/L4) and falsify the fixture-backed contract
  (L5). G4 and H migration stay RED and the campaign's remaining work never
  starts.
- **Persist parsed records into Qdrant beside chunks** — rejected: ADR 0010
  defines the Qdrant payload as the domain `Chunk` dump with filter-pushdown
  state; parsed records are not chunks and would reintroduce the
  `extra_forbidden` seam the round-trip contract now forbids (L12).
- **Promote `PaperRecord`/`PapersProvider` into core** — rejected: the finder
  and its port are API-local by L3, and ADR 0007 promoted only the shared
  finder fields on `PastPaperQuestion`. No core port or schema change (L14).
- **Persist only provenance, re-fetch question text on demand** — rejected:
  it keeps a network dependency on the read path and splits one record across
  two stores, which is the seam persistence exists to remove (L1, L4).

## Consequences

- G4 is green-lit: Lane D supplies the parsed-record table/migration behind
  its domain-local `MetadataStore`; Lane G wires the real provider behind the
  existing API-local `PapersProvider` port and retires the fixture-backed
  wording. The stored-record round-trip is G4's contract proof (L5, L12).
- Lane H migration is green-lit: `/api/papers` → `/api/v1/papers` plus
  `last_crawled` in the strict TS mirrors and `core-emitted.json` fixture. It
  is H-owned and does not wait on G4's store work.
- Lane B's parked persistence lines (`docs/PARKING_LOT.md:23` and `:39`) close
  with this ADR; Lane B does not implement the store (Lane D does).
- F4 is unaffected — it already runs on the pre-checkpoint pin and needs no
  storage or graph-orchestration work.
- Live crawling and live parsing stay parked (ADR 0003, fixtures only):
  persisting fixture-derived parsed records does not imply a live site.
- One ADR governs the rule. Changing what is persisted, where it lives, or
  the post-persistence gate requires a new ADR (L1).
