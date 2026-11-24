"""Settings fail fast with a clear error (L8)."""

import pytest

from uni_rag_core import ConfigError, Settings, get_settings, load_settings

REQUIRED = {"qdrant_url", "postgres_dsn", "minio_endpoint"}


def _env_names() -> list[str]:
    return [f"UNI_RAG_{name.upper()}" for name in Settings.model_fields]


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
