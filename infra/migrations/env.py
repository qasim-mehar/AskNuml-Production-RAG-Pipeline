"""Alembic environment for indexing metadata (L8/L13).

The DSN comes from the typed settings module unless a caller (tests) overrides
``sqlalchemy.url`` through the Alembic config. The target metadata is imported
from the adapter so migrations and domain protocols cannot drift unnoticed.
"""

from alembic import context
from sqlalchemy import engine_from_config, pool

from uni_rag_core import get_settings
from uni_rag_indexing.adapters.postgres_tables import metadata

config = context.config


def _dsn() -> str:
    """Return the configured DSN, falling back to typed settings only (L8)."""
    configured = config.get_main_option("sqlalchemy.url", "")
    return configured if configured else get_settings().postgres_dsn


def run_migrations_offline() -> None:
    """Emit SQL scripts without a live connection."""
    context.configure(
        url=_dsn(),
        target_metadata=metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    injected = config.attributes.get("engine")
    if injected is not None:
        with injected.connect() as connection:
            context.configure(connection=connection, target_metadata=metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()
        return
    section = config.get_section(config.config_ini_section, {})
    connectable = engine_from_config(
        section, prefix="sqlalchemy.", poolclass=pool.NullPool, url=_dsn()
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
