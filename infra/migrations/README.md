# Database migrations (Lane D)

Alembic environment owned by Lane D. The baseline `0001_initial` creates
`documents`, `chunks` and `crawl_state`, including soft-delete (`deleted_at`)
and `version` columns.

- The DSN is read only from `uni_rag_core.config.settings` (L8); a caller may
  override `sqlalchemy.url` through the Alembic config for isolated tests.
- `target_metadata` is imported from
  `uni_rag_indexing.adapters.postgres_tables`, the same definitions the adapter
  uses, so a schema drift is caught by a test rather than at runtime (L12).
- Apply with `uv run alembic -c infra/migrations/alembic.ini upgrade head`;
  revert with `uv run alembic -c infra/migrations/alembic.ini downgrade base`.
- Never hand-edit a schema: every change is a new Alembic revision (working
  agreement; repo L13 is about abstention on weak evidence, not migrations).
