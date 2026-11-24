# ADR 0007 — Provenance, metadata fields and core HTTP errors

- Status: Accepted
- Date: 2026-11-24
- Owners: Lane 0 (Foundation)
- Campaign: pipeline-mvp

## Context

Lanes B, C, E and H each reported the same class of friction: a fact they needed
was absent from a frozen schema, so they carried it in a domain-local model or
as text inside a human-readable field. E put `last_crawled` in a citation footer
and the next step in three-language prose; H renders a last-updated chip only
when a payload supplies it; B kept exam cover fields in `PaperMetadata`; C wrote
atomic-unit reasons as text lines; H's finder needs filter fields the question
schema lacks. None of them patched core (L14). These are schema gaps, not lane
bugs.

## Decision

Add the following fields, **all optional with defaults** so merged lane code
keeps compiling and every JSON payload from a lane still validates:

- `Citation.last_crawled: datetime | None = None` — L5 provenance at answer
  time. E's footer shim and H's conditional chip retire at migration.
- `Answer.next_step: str | None = None` and
  `Answer.abstention_reason: str | None = None` — structured L13 abstention
  output; E's three-language prose shim retires at migration.
- `PastPaperQuestion.course_code`, `.term`, `.exam_type`, `.department`
  (`str | None = None`) — B's `PaperMetadata` fields and H's finder filters.
- `ImageRef.image_url: str | None = None`. When present it follows the serve
  route convention `/api/images/{ref_id}`. No new core port: images still move
  through `ObjectStore` (L3); the route is an HTTP concern for Lane G.
- `Chunk.metadata: Mapping[str, str] | None = None` — structured producer
  notes, e.g. C's atomic-unit reasons, so consumers need not parse text.
- `Document.blocks: list[ContentBlock] = []`. We **promote the minimal shared
  block vocabulary** rather than keep it domain-local: `BlockKind`
  (`heading`, `paragraph`, `list_item`, `table`, `question`) and `ContentBlock`
  (`kind`, `text`, `index`, `level`, `table_rows`, `page`, `image_ref`) live in
  core. B emits them, C consumes them, and F's golden chunk references align on
  the same ordered structure. Keeping two domain-local `ParsedDocument` models
  would leave a seam that the integration pass must translate across, which is
  exactly the churn the frozen contracts exist to prevent (L3, L14).
- `AuthError`, `NotFoundError` and `RateLimitError` join the typed hierarchy in
  `uni_rag_core.errors`. G's API-local subclasses retire in its next milestone;
  G wires the HTTP status mapping then.

`AGENT.md` §3 (L6) is updated in lockstep for `Citation.last_crawled` and
`Chunk.metadata`. `tests/contracts/test_schema_v2.py` asserts every new field
both populated and absent through JSON, and asserts the new error types are
typed and catchable.

## Alternatives

- **Keep structured blocks domain-local with a documented seam** — rejected:
  B and C would each own a `ParsedDocument` with different shapes and F's
  golden data would need a third translation; the seam becomes permanent
  integration work rather than a contract.
- **Promote the full domain models** (parser pages/tables, chunk drafts) —
  rejected: only the ordered block vocabulary is shared; the rest stays with
  its owning lane (L9).
- **Make any new field required** — rejected: it would break merged lane code
  (L14).

## Consequences

- All lane shims named above are now optional migrations, not blockers; this
  wave does not touch lane code.
- Provenance and abstention become first-class answer fields (L5, L13), so the
  integration pass can read them without string parsing.
- Lane H can render `image_url` and `last_crawled` for real once Lane G emits
  them; Lane B retires `PaperMetadata` onto question fields.
- G's generated `openapi.json` artifact is regenerated from the existing script
  so the served contract stays byte-stable; no API code changed. Lane H's
  `core-emitted.json` fixture and TypeScript mirrors are regenerated/extended
  by Lane H at migration, because its strict mirrors do not yet declare the new
  optional fields.
