"""Shared fixtures and skip rules for compose-backed integration tests (L12)."""

from __future__ import annotations

import socket
from collections.abc import Iterator
from pathlib import Path

import pytest

from uni_rag_core import FakeClock, Settings

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_SERVICES: tuple[tuple[str, int], ...] = (
    ("qdrant", 6333),
    ("postgres", 5432),
    ("minio", 9000),
)


def pytest_configure(config: pytest.Config) -> None:
    """Register the integration marker so --strict-markers accepts it."""
    config.addinivalue_line(
        "markers", "integration: needs docker compose; skipped when services are absent"
    )


def _compose_ready() -> bool:
    """Return whether every compose service accepts a TCP connection."""
    for _host, port in COMPOSE_SERVICES:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                pass
        except OSError:
            return False
    return True


COMPOSE_AVAILABLE = _compose_ready()


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    """Typed settings pointing at the local compose stack (L8, no env reads here)."""
    return Settings(
        environment="local",
        qdrant_url="http://127.0.0.1:6333",
        postgres_dsn="postgresql://uni_rag:uni_rag@127.0.0.1:5432/uni_rag",
        minio_endpoint="http://127.0.0.1:9000",
        minio_access_key="minioadmin",
        minio_secret_key="minioadmin",
        minio_bucket="uni-rag",
        embedding_dimension=16,
        default_top_k=5,
        abstention_threshold=0.35,
        crawler={"seeds": ("http://127.0.0.1:8765/content-v1.html",)},
    )


@pytest.fixture(scope="session")
def fixed_clock() -> FakeClock:
    """A pinned clock for deterministic provenance assertions (L4)."""
    return FakeClock()


@pytest.fixture
def skip_without_compose() -> Iterator[None]:
    """Skip the requesting test unless the compose services are reachable."""
    if not COMPOSE_AVAILABLE:
        pytest.skip("docker compose services are not running on this host")
    yield
