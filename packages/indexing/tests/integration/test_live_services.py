"""Live compose checks. Skipped unless the service is actually reachable.

`make up` belongs to Lane 0; these tests never start containers themselves.
"""

from __future__ import annotations

import socket

import pytest
from sqlalchemy import create_engine

from tests.contracts.port_contracts import (
    assert_object_store_contract,
    assert_vector_store_contract,
)
from tests.factories import FIXED_TIME
from uni_rag_core import ConfigError, FakeClock, load_settings
from uni_rag_indexing.adapters.minio_object_store import MinioObjectStore
from uni_rag_indexing.adapters.qdrant_vector_store import QdrantVectorStore


def _reachable(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex(("localhost", port)) == 0


def _settings() -> object:
    try:
        return load_settings()
    except ConfigError as exc:
        pytest.skip(f"settings unavailable: {exc}")


@pytest.mark.integration
def test_qdrant_live_vector_store_contract() -> None:
    if not _reachable(6333):
        pytest.skip("qdrant compose service unreachable on :6333")
    settings = _settings()
    store = QdrantVectorStore.from_settings(settings, clock=FakeClock(FIXED_TIME))  # type: ignore[arg-type]
    assert_vector_store_contract(store)


@pytest.mark.integration
def test_minio_live_object_store_contract() -> None:
    if not _reachable(9000):
        pytest.skip("minio compose service unreachable on :9000")
    settings = _settings()
    store = MinioObjectStore.from_settings(settings)  # type: ignore[arg-type]
    assert_object_store_contract(store)


@pytest.mark.integration
def test_postgres_live_migration_apply_and_revert() -> None:
    if not _reachable(5432):
        pytest.skip("postgres unreachable on :5432")
    settings = _settings()
    engine = create_engine(settings.postgres_dsn)  # type: ignore[attr-defined]
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
    except Exception as exc:  # noqa: BLE001 - skip only when the configured DSN is not usable
        pytest.skip(f"configured postgres DSN not usable here: {exc}")
    from pathlib import Path

    from alembic import command
    from alembic.config import Config

    root = Path(__file__).resolve().parents[4]
    cfg = Config(str(root / "infra" / "migrations" / "alembic.ini"))
    cfg.set_main_option("script_location", str(root / "infra" / "migrations"))
    cfg.set_main_option("sqlalchemy.url", settings.postgres_dsn)  # type: ignore[attr-defined]
    command.upgrade(cfg, "head")
    try:
        with engine.connect() as connection:
            assert {"documents", "chunks", "crawl_state"} <= set(
                connection.exec_driver_sql(
                    "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                ).scalars()
            )
    finally:
        command.downgrade(cfg, "base")
