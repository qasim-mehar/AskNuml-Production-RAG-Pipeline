# Lane H → Lane G contract expectations

Lane H ships against the frozen `Query`/`Answer`/`Citation`/`ImageRef`/
`PastPaperQuestion` schemas and a deterministic mock fetch router. Lane G has not
merged its OpenAPI yet, so the endpoints below are the contract Web expects.
They are not implemented by Web; swapping `lib/api/mocks/handlers.ts` for the real
client should require no component changes.

| Method | Path | Request | Response |
| --- | --- | --- | --- |
| POST | `/api/query` | frozen `Query` JSON | frozen `Answer` JSON |
| POST | `/api/query/stream` | frozen `Query` JSON | `text/event-stream` (below) |
| POST | `/api/feedback` | `{ answer_id, query_id?, sentiment: "positive"\|"negative", reason? }` | `204` |
| GET | `/api/papers?course_code=&year=&term=&exam_type=&department=` | — | `{ results: PastPaperQuestion[] }` |
| GET | `/api/images/{ref_id}` | object-store key path segment | image bytes |

Every response must carry `x-request-id` (or `x-trace-id` / `traceparent`);
Web reads it into typed `ApiError`s and structured logs. All payloads are
validated with strict Zod mirrors at the edge (`lib/api/schemas.ts`).

## SSE event contract

Each frame is `event: <name>` + `data: <json>`:

- `token` — `{ "type": "token", "text": string }` (incremental answer text)
- `citation` — `{ "type": "citation", "citation": Citation }`
- `image` — `{ "type": "image", "image": ImageRef }`
- `answer` — `{ "type": "answer", "answer": Answer }` (authoritative final event)
- `error` — `{ "type": "error", "code": string, "message": string }`

A stream without a final `answer` event, or with an event that fails validation,
is a typed error state in Web — never a partial render.

## Open items requiring Lane 0 / Lane G action (CONTRACT-CHANGE)

- **Citation last-updated date.** ADR 0004 asks citation chips to show a
  last-updated date, but the frozen core `Citation` has no `last_crawled` field.
  `CitationSchema` carries an optional, strictly forward-compatible
  `last_crawled`; the chip renders it only when a payload supplies it. Core must
  add the field before Lane G may emit it.
- **Finder result labels.** `PastPaperQuestion` lacks `course_code`, `term`,
  `exam_type` and `department`, so results are rendered from the fields the
  schema does carry; the filter values are sent as query parameters and shown as
  the user's own selection, never as payload facts.
- **Image bytes.** `ImageRef` has `ref_id` but no browser-fetchable URL; Web
  assumes an `/api/images/{ref_id}` object-store proxy (or wants an `image_url`
  field added to `ImageRef`).
- **Feedback endpoint scope.** ADR 0004 says feedback is local UI state only,
  while the Lane H mission requires a mocked feedback POST and a Lane G endpoint
  expectation. Lane 0 should reconcile the ADR before Lane G builds the route;
  until then the UI accepts the success/failure result of the response honestly.
- **Contract fixture source.** `src/lib/api/mocks/core-emitted.json` is produced
  by `apps/web/scripts/generate_contract_fixture.py` from the Pydantic models;
  regenerate it whenever Lane 0 changes a frozen schema.
