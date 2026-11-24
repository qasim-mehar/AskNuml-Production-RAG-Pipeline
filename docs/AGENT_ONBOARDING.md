# Agent Onboarding

## 1. Workflow

- **One conversation per lane.** Each lane runs in its own conversation with a single, focused mission. Do not mix lanes in one session.
- **Own branch or worktree.** Every lane works on its own branch or worktree. Do not commit to another lane's branch.
- **Lane 0 freezes contracts first.** Lanes A to H do not begin until Lane 0 has frozen the core ports, schemas and settings. Read the frozen contracts; do not redefine them.
- **Never edit another lane's files.** Ownership is exact and enforced by CODEOWNERS. If you need a change outside your owned directories, stop.
- **Escalate contract disagreements as ADRs.** If a contract is wrong or missing, open a `CONTRACT-CHANGE` PR (Lane 0) with an ADR; do not patch around it locally.

## 2. System map

See `docs/ARCHITECTURE.md` for the full flow. The retrieval box is:

```
route -> filter -> search -> grade -> (rewrite loop | rerank) -> answer | abstain | clarify
```

`filter` is a metadata filter over department and other fields, backed by a config row. It is never a graph branch. Existing lane prompts predate L15-L17; see `docs/PARKING_LOT.md`.

## 3. Lane model

| Lane | Name | Owns |
|------|------|------|
| 0 | Foundation | `packages/core/`, `infra/`, `.github/`, `docs/`, root config |
| A | Crawler | `packages/ingestion/crawler/` |
| B | Parsing | `packages/ingestion/parsers/` |
| C | Chunking and enrichment | `packages/ingestion/chunking/`, `packages/ingestion/enrichment/` |
| D | Indexing and storage | `packages/indexing/`, `infra/migrations/` |
| E | Retrieval | `packages/retrieval/` (includes planned `graph/` and provider adapters in `packages/retrieval/src/uni_rag_retrieval/adapters/`) |
| F | Evaluation | `packages/eval/`, `eval/` |
| G | API | `apps/api/` |
| H | Web | `apps/web/` |

Lane E builds the graph against fakes and ships the linear pipeline (route, filter, search, grade, rerank, answer) first. Loops and branches come later, one at a time, each with an eval row (L16).

## 4. Prompt structure

Every generated lane prompt uses these eight sections in this order:

1. CONTEXT ANCHORS
2. MISSION
3. LAW COMPLIANCE
4. FILE PLAN
5. TEST PLAN
6. QUALITY PASS (before gates)
7. GREEN GATES + COMMIT
8. HANDOFF

## 5. Prompt template

The following is the exact template used to generate a lane prompt. Populate every placeholder; paste anchor paths only, without restating anchor contents.

```markdown
You are working in the uni-rag monorepo as lane {{LANE}} ({{LANE_NAME}}).

1. CONTEXT ANCHORS
   Read these before doing anything else; use them, do not restate them:
   - `AGENT.md` (binding laws, Definition of Done, lane model)
   - `docs/ARCHITECTURE.md` (system map and data flow)
   - `docs/AGENT_ONBOARDING.md` (workflow and lane briefs)
   - `docs/PROGRESS.md` (lane board)
   - `docs/adr/` (decision records)

2. MISSION
   Deliver exactly this milestone: {{MILESTONE}}

3. LAW COMPLIANCE
   Laws in scope: {{LAWS}}. All lanes are always bound by L1, L5, L10, L11 and L12. Name each law you touch.

4. FILE PLAN
   You own only: {{OWNED_DIRS}}. Read-only: `packages/core/` (Lane 0) and {{FORBIDDEN_DIRS}}. Consume the frozen core ports and schemas as-is (L3); define any new Protocol domain-local, never in core without a CONTRACT-CHANGE PR and ADR. Create or edit nothing else.

5. TEST PLAN
   Write fixtures first, then behaviour tests. Fakes: {{FAKES}}. Fixtures: {{FIXTURES}}. Fakes are deterministic (L4). Unit tests touch no real network, LLM or paid API.

6. QUALITY PASS (before gates)
   Spawn a fresh review subagent with your diff. Fix what it finds or log it in the handoff.

7. GREEN GATES + COMMIT
   Run and pass exactly: {{GATES}}. Then commit with the campaign tag from `AGENT.md`. Lane 0 updates `docs/PROGRESS.md` on merge; do not edit it.

8. HANDOFF
   Report in at most 25 lines:
   - Lane / milestone:
   - Files created or changed (paths):
   - Ports implemented or consumed:
   - Gates run and result:
   - Contract issues / ADRs raised:
   - Blocked by / next lane handoff:
```

## 6. Lane briefs

### Lane E: Retrieval

- Own the LangGraph state graph under `packages/retrieval/src/uni_rag_retrieval/graph/` (planned). Graph nodes are thin wrappers; logic lives in plain modules under `packages/retrieval/src/uni_rag_retrieval/service/`, so it is unit-testable without the graph (L15).
- Use the graph only for retry on weak retrieval (grade, rewrite the query, search again, capped loop), clarification when a required filter is missing, multi-hop answers that reference another document, the abstain branch and checkpointed follow-up state.
- Keep route, filter, search, rerank and answer linear. Department is a metadata filter and a config row, never a graph branch.
- Add a `google-genai` adapter for `LLM`, `Embedder` and page images, plus one second adapter (`openai` or a local model). Page-image handling stays inside the adapter: use `ImageRef` and `ObjectStore` and add no new core port (L3). Both pass the shared contract test in `tests/contracts/` (L17). Provider comparison is an eval run, not a graph branch.

### Lane D: Indexing and storage

- Keep `packages/indexing/` free of provider code. The `google-genai` and second-provider adapters are Lane E's; implement only `VectorStore` and `ObjectStore` adapters here.

## 7. Working agreements

- Prove each graph node in the ablation table. A node with no measured gain is removed (L16). Lane E supplies node purposes and required eval rows in its handoff; Lane F writes the ablation table in `packages/eval/`.
- Framework imports stay inside the planned `graph/` and provider-adapter directories under `packages/retrieval/` (L15); the framework-free zones in `AGENT.md` §4 still apply.
- Provider behavior stays inside its adapter (L17).
- Valid law references: L1, L2, L3, L4, L5, L6, L7, L8, L9, L10, L11, L12, L13, L14, L15, L16, L17. They are defined in `AGENT.md`.
