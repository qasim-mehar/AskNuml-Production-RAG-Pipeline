# Lane H — Web

You are working in the uni-rag monorepo as lane H (Web).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records; ADR 0004 promotes this UI scope)

2. MISSION
   Deliver exactly this milestone: a Next.js App Router shell with the existing
   static health page, a typed `fetchJson` client in `src/lib/`, and the
   `components/`, `features/` and `hooks/` directories wired for composition.
   Per ADR 0004, build the student-facing UI: cited chat with streaming, a
   past-paper finder and feedback capture, against the frozen `Query`/`Answer`
   schemas mirrored in TypeScript and a mocked API until Lane G's OpenAPI
   lands. Components are presentational and never fetch; TypeScript is strict;
   no live backend is required for tests. No core schema, port or setting
   change.

3. LAW COMPLIANCE
   Laws in scope: L2, L4, L7, L9, L12. All lanes are always bound by L1, L5,
   L10, L11 and L12. Name each law you touch. Render citations and past-paper
   page images from the schema fields when an answer contains them (L5); support
   RTL text for Urdu (L7); `lib/` holds pure functions and the API client (no
   React), `components/` is presentational (no fetching), `features/` composes
   UI with hooks (L9).

4. FILE PLAN
   You own only: `apps/web/`. Read-only: `packages/core/` (Lane 0) and
   `apps/api/`, `packages/`, `eval/`, `infra/`, root config (there is no root
   `package.json`; do not create one) and all other lanes' dirs. Consume the
   frozen core ports and schemas as-is (L3); define any new Protocol domain-local,
   never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing
   else. There are no Python core ports: consume the API contract via
   `fetchJson<Answer>` where `Answer`, `Citation`, `Query` and `ImageRef` mirror
   the frozen core schemas in TypeScript; define these types in `src/lib/` and
   do not modify core.

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: none in Python; mock
   `fetchJson` with `vitest` fixtures. Fixtures:
   `tests/fixtures/golden/mini-golden.json` for representative question text
   (including Urdu/Roman Urdu) used in UI tests. All test data is deterministic
   (L4). Unit tests touch no real network, LLM or paid API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in
   the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly:
   ```
   pnpm --dir apps/web lint
   pnpm --dir apps/web typecheck
   pnpm --dir apps/web test
   make lint
   make type
   make test
   ```
   Then confirm the root gates are green, and commit with the campaign tag from
   `AGENT.md`. Lane 0 updates `docs/PROGRESS.md` on merge; do not edit it.

8. HANDOFF
   Report in at most 25 lines:
   - Lane / milestone:
   - Files created or changed (paths):
   - Ports implemented or consumed:
   - Gates run and result:
   - Contract issues / ADRs raised:
   - Blocked by / next lane handoff:
