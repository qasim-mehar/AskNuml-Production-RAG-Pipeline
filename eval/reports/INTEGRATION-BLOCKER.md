# Integration blocker — new CONTRACT-CHANGE (Lane 0)

- Campaign: `pipeline-mvp`
- Found while running Lane F's harness against the integrated pipeline after all
  eight swaps were committed with green gates.
- Symptom: `Chunk.model_validate(hit.payload)` in
  `packages/retrieval/src/uni_rag_retrieval/service/pipeline.py:108` raises
  `extra_forbidden` for `last_crawled_ts`, `department`, `course_code`, `year`,
  `term`, `is_live`, `indexed_at`, `deleted_at` and `superseded_by`.
- Cause: Lane D's `build_payload` adds these index fields to the Qdrant payload;
  Lane E assumes `VectorHit.payload` is exactly the frozen `Chunk` shape.
- Status: **STOPPED**, as the master prompt requires for a new contract change.
  No threshold was changed, no lane code was edited, no fake was presented as a
  real run. The earlier report from a run with an unpopulated vector store was
  deleted because it was not valid hybrid-search evidence.
- Required follow-up: Lane 0 CONTRACT-CHANGE PR touching only `packages/core`,
  with an ADR defining the payload-vs-Chunk boundary (e.g. optional index fields
  or a dedicated payload schema). It must not be folded into a swap commit.
- First integrated numbers: **blocked**; no table is published from an invalid run.
