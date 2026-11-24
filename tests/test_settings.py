"""Settings fail fast with a clear error (L8)."""

import pytest
from pydantic import BaseModel

from uni_rag_core import (
    ApiSection,
    ConfigError,
    CrawlerSection,
    ProvidersSection,
    Settings,
    get_settings,
    load_settings,
)
from uni_rag_core.config import SECTION_ENV_PREFIXES

REQUIRED = {"qdrant_url", "postgres_dsn", "minio_endpoint"}
SECTION_TYPES: dict[str, type[BaseModel]] = {
    "api": ApiSection,
    "crawler": CrawlerSection,
    "providers": ProvidersSection,
}


def _env_names() -> list[str]:
    names = ["CI"]
    names.extend(f"UNI_RAG_{name.upper()}" for name in Settings.model_fields)
    for section, section_type in SECTION_TYPES.items():
        prefix = SECTION_ENV_PREFIXES[section]
        names.extend(f"{prefix}{name.upper()}" for name in section_type.model_fields)
    return names


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    for name in _env_names():
        monkeypatch.delenv(name, raising=False)
    get_settings.cache_clear()
    return monkeypatch


def test_missing_required_settings_fail_fast(clean_env: pytest.MonkeyPatch) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_settings()
    message = str(excinfo.value)
    for field in REQUIRED:
        assert field in message
    assert "UNI_RAG_" in message


def test_valid_settings_load(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("UNI_RAG_QDRANT_URL", "http://localhost:6333")
    clean_env.setenv("UNI_RAG_POSTGRES_DSN", "postgresql://user:pass@localhost/db")
    clean_env.setenv("UNI_RAG_MINIO_ENDPOINT", "http://localhost:9000")
    settings = load_settings()
    assert settings.qdrant_url == "http://localhost:6333"
    assert settings.default_top_k == 10
    assert settings.abstention_threshold == 0.35


def test_settings_are_cached(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("UNI_RAG_QDRANT_URL", "http://localhost:6333")
    clean_env.setenv("UNI_RAG_POSTGRES_DSN", "postgresql://user:pass@localhost/db")
    clean_env.setenv("UNI_RAG_MINIO_ENDPOINT", "http://localhost:9000")
    assert get_settings() is get_settings()


def test_settings_are_frozen(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("UNI_RAG_QDRANT_URL", "http://localhost:6333")
    clean_env.setenv("UNI_RAG_POSTGRES_DSN", "postgresql://user:pass@localhost/db")
    clean_env.setenv("UNI_RAG_MINIO_ENDPOINT", "http://localhost:9000")
    settings = load_settings()
    with pytest.raises((TypeError, ValueError)):
        settings.app_name = "changed"  # type: ignore[misc]
