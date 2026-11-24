# Agent Onboarding

## Workflow

- **One conversation per lane.** Each lane runs in its own conversation with a
  single, focused mission. Do not mix lanes in one session.
- **Own branch/worktree.** Every lane works on its own branch (or worktree).
  Do not commit to another lane's branch.
- **Lane 0 freezes contracts first.** Lanes A–H do not begin until Lane 0 has
  frozen the core ports, schemas and settings. Read the frozen contracts; do not
  redefine them.
- **Never edit another lane's files.** Ownership is exact and enforced by
  CODEOWNERS. If you need a change outside your owned directories, stop.
- **Escalate contract disagreements as ADRs.** If a contract is wrong or
  missing, open a `CONTRACT-CHANGE` PR (Lane 0) with an ADR — do not patch
  around it locally.

## Lane model

See `AGENT.md` → "How we work: parallel lanes" and `docs/PROGRESS.md` for the authoritative lane
list and ownership map. Lane 0 owns `packages/core/`, `infra/`, `.github/`,
`docs/` and root config; lanes A–H own the ingestion, indexing, retrieval, eval,
API and web directories respectively.

## Prompt template

The following is the exact template used to generate a lane prompt. Populate
every placeholder; paste anchor paths only — do not restate anchor contents
inline.

```markdown
You are working in the uni-rag monorepo as lane {{LANE}} ({{LANE_NAME}}).

1. **Role and context anchors.** Read these anchors before doing anything else;
   do not restate them here, just use them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (this workflow)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. **Mission and milestone.** Deliver exactly this milestone: {{MILESTONE}}

3. **Ownership and boundaries.** You own ONLY these dirs: {{OWNED_DIRS}}
   Forbidden (read-only):
   - `packages/core/` (Lane 0 only)
   - {{FORBIDDEN_DIRS}}
   Do not create or edit files anywhere else.

4. **Ports and contracts.** The core ports/protocols you implement or consume:
   {{PORTS}}
   Schema names you must honour: `Chunk`, plus the port-level request/response
   types defined in `packages/core/src/uni_rag_core/`. Use them as-is.

5. **Fakes and fixtures available.** While other lanes are blocked, use these
   fakes and fixture files:
   - Fakes: {{FAKES}}
   - Fixtures: {{FIXTURES}}
   All fakes are deterministic (L4). Do not reach for real network or models.

6. **Laws in scope.** These laws apply to your work: {{LAWS}}
   All lanes are always bound by L1, L5, L10, L11 and L12 unless stated.

7. **Definition of done and green gates.** Run and pass exactly:
   {{GATES}}
   Docs inside your owned directories must agree with code, and no parking-lot
   work. Lane 0 updates `docs/PROGRESS.md` on merge — do not edit it.

8. **Handoff.** Report back in at most 25 lines, in this format:
   - Lane / milestone:
   - Files created or changed (paths):
   - Ports implemented/consumed:
   - Gates run and result:
   - Contract issues / ADRs raised:
   - Blocked by / next lane handoff:
```
