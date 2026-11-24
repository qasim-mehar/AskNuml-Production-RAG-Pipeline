# ADR 0003 — Real parse and fetch adapters

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

Lanes A and B currently build against fakes and fixtures only, which cannot
validate extraction quality on real PDF/HTML shapes. Promoting parsing and a
real fetcher is a scope change under `docs/PARKING_LOT.md` and needs an ADR
before those lanes rely on it (L1). Provenance must remain traceable to a source
URL and `last_crawled` (L5, L6), and unit tests must never touch the live
university site (L4).

## Decision

Promote fixture-driven Docling (digital PDFs) and MinerU (scanned pages) parsing
for Lane B, and a real HTTP `Fetcher` adapter for Lane A tested against a local
test server. Fakes and fixtures remain the default in tests; the real adapters
are exercised only against checked-in fixtures or the local server, behind the
frozen ports with no new core port or schema. Large-scale live crawling of the
university site stays parked.

## Consequences

Lanes A and B can validate real extraction fidelity without network access or
paid services, and CI stays deterministic. Every parsed item still carries
`source_url`, `last_crawled` and page/image provenance so answers can cite real
sources (L5, L6). A future live crawler needs a separate ADR; this one grants
fixture/local-server scope only.
