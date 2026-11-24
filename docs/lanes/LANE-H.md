# Lane H — Web

You are working in the uni-rag monorepo as lane H (Web).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: a Next.js App
   Router shell with the existing static health page, a typed `fetchJson`
   client in `src/lib/`, and the empty `components/`, `features/`, `hooks/`
   directories wired for later lanes. Components are presentational and never
   fetch. TypeScript strict. Do **not** build a past-paper finder or chat UI —
   those are parked in `docs/PARKING_LOT.md` until the API and retrieval lanes
   provide real contracts. Stub API responses in tests; no live backend.

3. **Ownership and boundaries.** You own ONLY these dirs:
   `apps/web/`.
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - `apps/api/`, `packages/`, `eval/`, `infra/`, root config (`package.json` at
     repo root does not exist; do not create one) and all other lanes' dirs.
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   - No Python core ports. Consume the API contract via `fetchJson<Answer>`
     where `Answer`, `Citation` and `ImageRef` mirror the frozen core schemas in
     TypeScript. Define these types in `src/lib/`; do not modify core.
   - `lib/` holds pure functions and the API client (no React); `components/`
     holds presentational UI only; `features/` composes UI with hooks.

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: none in Python; mock `fetchJson` with `vitest` fixtures.
   - Fixtures: `tests/fixtures/golden/mini-golden.json` for representative
     question text (including Urdu/Roman Urdu) used in UI tests.
   All test data is deterministic (L4). No network calls in tests.

6. **Laws in scope.** These laws apply to your work: L2, L4, L7, L9, L12.
   All lanes are always bound by L1, L5, L10, L11 and L12 unless stated. Render
   citations and past-paper page images when an answer contains them (L5);
   support RTL text for Urdu (L7).

7. **Definition of done and green gates.** Run and pass exactly:
   ```
   pnpm --dir apps/web lint
   pnpm --dir apps/web typecheck
   pnpm --dir apps/web test
   ```
   Then confirm the root `make lint`, `make type` and `make test` are green
   before handoff. Docs inside your owned directories must agree with code, and
   no parking-lot work. Lane 0 updates `docs/PROGRESS.md` on merge — do not
   edit it.

8. **Handoff.** Report back in at most 25 lines, in this format:
   - Lane / milestone:
   - Files created or changed (paths):
   - Ports implemented/consumed:
   - Gates run and result:
   - Contract issues / ADRs raised:
   - Blocked by / next lane handoff:
