# Lane H → Lane G contract reconciliation (milestone 2)

Source of truth: `apps/api/openapi.json` on this branch. **State at swap time:** the
artifact is the contract-wave regeneration — it carries the ADR-0007 schema fields
(`Citation.last_crawled`, `ImageRef.image_url`, `Answer.next_step`,
`Answer.abstention_reason`) but does **not** declare the feedback, image-serving or
papers routes. Lane G's G2 route work is not present here. Routes not in the
artifact are marked below and filed as CONTRACT-CHANGE notes; Web does not claim
they are artifact-backed. Tests assert the artifact-resolved routes against
`mocks/openapi-emitted.json`, generated from the artifact by
`apps/web/scripts/generate_contract_fixture.py`.

## Endpoint reconciliation

| Milestone-1 assumption | Artifact / ADR status | Web implementation |
| --- | --- | --- |
| `POST /api/query` | **Resolved:** artifact `POST /api/v1/query` (200 → `Answer`; 401/422/429/503 → `ErrorBody`; `X-API-Key` security) | `query()` posts a strict `Query` to the artifact path and validates `Answer`. Auth remains out of H's scope. |
| `POST /api/query/stream` | **Resolved:** artifact `POST /api/v1/query/stream`; its 200 has no declared content schema. Framing lives in `uni_rag_api.schemas` (ADR 0009: API-local SSE envelopes). | `stream()` posts the same `Query`, parses `token` + final `citations`, validates both. |
| SSE `token` = `{type,text}`; `citation`, `image`, `answer`, `error` events | **Superseded:** real events are `token` = `{ token }` (`TokenEvent`) and `citations` = `{ answer }` (`CitationsEvent`). No `citation`/`image`/`answer`/`error` event is emitted. Non-2xx errors are HTTP `ErrorBody`, not an SSE frame. | Retired the four invented event handlers; unknown SSE names become a typed `unknown_stream_event` error. Provenance renders only from the final validated `Answer`. |
| `POST /api/feedback`, `204` | **Superseded by ADR 0009:** `POST /api/v1/feedback`, `202` whose body echoes the validated payload, `x-request-id` on success and failure, `422 ErrorBody` on unknown/invalid fields. Artifact lacks the route → CONTRACT-CHANGE. | `feedback()` validates the echo with `FeedbackResponseSchema`, returns `{accepted, requestId, response}` on 202 and a typed `ApiError` on 422. |
| `GET /api/papers?course_code=&year=&term=&exam_type=&department=` | **Unresolved:** no artifact route and no `PastPaperQuestion` schema. Result labels are in core via ADR 0007. → CONTRACT-CHANGE. | `papers()` keeps the milestone-1 path and query keys, validates `{ results: PastPaperQuestion[] }` against the core-derived schema. |
| `GET /api/images/{ref_id}` | **Partially resolved:** ADR 0007 defines the convention and the artifact adds `ImageRef.image_url`; no artifact route → CONTRACT-CHANGE. | `imageSrcFor()` uses `image_url` when present, else `/api/images/{encoded ref_id}`; a failed load becomes an explicit status message, never a broken frame. |
| `x-request-id` (or `x-trace-id`/`traceparent`) on every response | **Partial:** artefact does not document headers; ADR 0009 requires it for feedback, trace middleware supplies it for queries. → CONTRACT-CHANGE (document the header). | `requestIdFrom()` captures it on 2xx and non-2xx; every `ApiError` carries it and `logClientError` logs it as structured JSON. |
| `Citation.last_crawled` forward-compatible chip | **Resolved:** real field in core (ADR 0007) and in the artifact's `Citation`. | Chip renders the payload date (formatted for display) when present and nothing when absent. |
| Finder result labels absent from `PastPaperQuestion` | **Resolved in core** (ADR 0007 adds `course_code`, `term`, `exam_type`, `department`); still absent from the artifact's schema set. | Zod mirror carries the four fields with defaults; filters stay user-selected UI values, never payload facts. |
| Image bytes had no browser URL | **Resolved:** `ImageRef.image_url` is in core and the artifact (ADR 0007). | Consumed as above. |
| Feedback was local-only UI state with a mocked POST | **Resolved:** ADR 0009 grants a real local-only `202` echo that persists nothing. | UI reports acceptance honestly and does not imply persistence. |
| Fixture source | **Resolved:** generated from core Pydantic dumps **and** the OpenAPI artifact. | `core-emitted.json` + `openapi-emitted.json`; both round-trip through the Zod mirrors in `schemas.test.ts`. |

## CONTRACT-CHANGE notes for Lane 0 / Lane G (swap-time backlog)

1. Add `POST /api/v1/feedback` to `openapi.json` with the ADR 0009 request, `202`
   echo response and `422 ErrorBody`; the route implementation is not in this artifact.
2. Add the papers finder route (path to confirm) and `PastPaperQuestion` schema to
   `openapi.json`; Web currently holds the milestone-1 `/api/papers` assumption.
   **Resolved by G3 / M4:** the artifact declares `GET /api/v1/papers` with
   `PaperRecord`/`PaperSearchResult`; Web now calls that route (see below).
3. Add `GET /api/images/{ref_id}` with its image response content type; the
   `image_url` convention alone is not a served route in the artifact.
4. Document `x-request-id` on every operation (or add the trace header to the
   artifact's documented headers) so error correlation is contract-backed.
   **Resolved by G3:** the served artifact documents `x-request-id` on every
   operation, including the papers route.
5. Document the two SSE envelopes in the artifact, or state in its description that
   they are API-local per ADR 0009; today the 200 stream has no schema at all.
6. The artifact declares `ApiKeyAuth` on the query routes. Web does not send or
   manage an API key (auth is out of scope); the fake backend used for the
   Lighthouse run leaves the header unenforced and is labelled as such.

## Fixture provenance (L12, L4)

`uv run python apps/web/scripts/generate_contract_fixture.py` regenerates both
fixtures deterministically: `core-emitted.json` from the frozen Pydantic models
(with ADR-0007 fields populated) and `openapi-emitted.json` from the served
artifact's `components.schemas` and `operationId`s. Tests never call the live API;
the fetch router in `mocks/handlers.ts` serves these shapes from `globalThis.fetch`.

## Milestone 4 — papers migration (G3 artifact, ADR 0011)

The milestone-2 rows above are kept as the swap-time record. The served artifact
now declares `GET /api/v1/papers` (`find_papers_api_v1_papers_get`): the five
finder filters (`course_code`, `year`, `term`, `exam_type`, `department`), with
`limit`/`offset` pagination defaults left to the artifact; a strict
`{"results": []}` 200 on no match; `ErrorBody` on 401/422/429/503; and
`x-request-id` on every response. Its `PaperRecord` is the ADR 0007
`PastPaperQuestion` plus a required `last_crawled` date-time string, wrapped in a
strict `PaperSearchResult`. Web's `papers()` now calls the artifact path, the
strict TS mirror includes `PaperRecord`, and both generated fixtures carry the
field, so route and mirror drift fail the suite.
