"""Settings contract: one module, nested sections, fail-fast, live-flag safety."""

import pytest
from pydantic import BaseModel

from uni_rag_core import (
    ApiSection,
    ConfigError,
    CrawlerSection,
    ProvidersSection,
    Settings,
    load_settings,
)
from uni_rag_core.config import SECTION_ENV_PREFIXES

SECTION_TYPES: dict[str, type[BaseModel]] = {
    "api": ApiSection,
    "crawler": CrawlerSection,
    "providers": ProvidersSection,
}
REQUIRED_ENV = {
    "UNI_RAG_QDRANT_URL": "http://localhost:6333",
    "UNI_RAG_POSTGRES_DSN": "postgresql://user:pass@localhost/db",
    "UNI_RAG_MINIO_ENDPOINT": "http://localhost:9000",
}


def _all_env_names() -> list[str]:
    names = [f"UNI_RAG_{name.upper()}" for name in Settings.model_fields]
    for section, section_type in SECTION_TYPES.items():
        prefix = SECTION_ENV_PREFIXES[section]
        names.extend(f"{prefix}{name.upper()}" for name in section_type.model_fields)
    return names


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """Isolate every env var the settings module can read."""
    for name in _all_env_names():
        monkeypatch.delenv(name, raising=False)
    for name, value in REQUIRED_ENV.items():
        monkeypatch.setenv(name, value)
    return monkeypatch


def test_nested_sections_live_in_the_single_settings_module(clean_env: pytest.MonkeyPatch) -> None:
    settings = load_settings()
    assert isinstance(settings.api, ApiSection)
    assert isinstance(settings.crawler, CrawlerSection)
    assert isinstance(settings.providers, ProvidersSection)


def test_api_section_keeps_g_defaults(clean_env: pytest.MonkeyPatch) -> None:
    api = load_settings().api
    assert api.auth_enabled is False
    assert api.api_key == "local-dev-key"
    assert api.rate_limit_capacity == 30
    assert api.max_top_k == 20
    assert api.trace_header == "X-Trace-Id"
    assert api.trace_header_enabled is True


def test_legacy_api_env_keys_are_read(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("UNI_RAG_API_AUTH_ENABLED", "true")
    clean_env.setenv("UNI_RAG_API_RATE_LIMIT_CAPACITY", "7")
    clean_env.setenv("UNI_RAG_API_TRACE_HEADER", "X-Custom-Trace")
    clean_env.setenv("UNI_RAG_API_TRACE_HEADER_ENABLED", "false")
    api = load_settings().api
    assert api.auth_enabled is True
    assert api.rate_limit_capacity == 7
    assert api.trace_header == "X-Custom-Trace"
    assert api.trace_header_enabled is False


def test_legacy_crawler_env_keys_are_read(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("UNI_RAG_CRAWLER_SEEDS", '["https://example.edu/"]')
    clean_env.setenv("UNI_RAG_CRAWLER_MAX_DEPTH", "4")
    clean_env.setenv("UNI_RAG_CRAWLER_REQUESTS_PER_SECOND", "2.5")
    clean_env.setenv("UNI_RAG_CRAWLER_USER_AGENT", "uni-rag-test/1.0")
    crawler = load_settings().crawler
    assert crawler.seeds == ("https://example.edu/",)
    assert crawler.max_depth == 4
    assert crawler.requests_per_second == 2.5
    assert crawler.user_agent == "uni-rag-test/1.0"


def test_live_providers_default_off_and_keys_are_never_logged(
    clean_env: pytest.MonkeyPatch,
) -> None:
    clean_env.setenv("UNI_RAG_PROVIDERS_GOOGLE_API_KEY", "do-not-log-this-key")
    providers = load_settings().providers
    assert providers.live_enabled is False
    assert "do-not-log-this-key" not in providers.model_dump_json()
    assert "do-not-log-this-key" not in repr(providers)


def test_live_providers_cannot_be_enabled_in_ci(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.setenv("UNI_RAG_ENVIRONMENT", "ci")
    clean_env.setenv("UNI_RAG_PROVIDERS_LIVE_ENABLED", "true")
    with pytest.raises(ConfigError, match="Invalid settings"):
        load_settings()


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("UNI_RAG_API_RATE_LIMIT_CAPACITY", "0"),
        ("UNI_RAG_API_MAX_TOP_K", "0"),
        ("UNI_RAG_CRAWLER_REQUESTS_PER_SECOND", "0"),
        ("UNI_RAG_CRAWLER_MAX_DEPTH", "-1"),
        ("UNI_RAG_CRAWLER_SEEDS", '["ftp://example.edu/"]'),
        ("UNI_RAG_CRAWLER_USER_AGENT", "   "),
    ],
)
def test_invalid_nested_values_fail_fast(
    clean_env: pytest.MonkeyPatch, name: str, value: str
) -> None:
    clean_env.setenv(name, value)
    with pytest.raises(ConfigError):
        load_settings()


def test_required_infrastructure_still_fails_fast(clean_env: pytest.MonkeyPatch) -> None:
    clean_env.delenv("UNI_RAG_MINIO_ENDPOINT")
    with pytest.raises(ConfigError, match="minio_endpoint"):
        load_settings()
