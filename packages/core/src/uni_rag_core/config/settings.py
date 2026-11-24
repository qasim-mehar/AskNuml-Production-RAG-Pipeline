"""The single typed settings module (L8).

No other module may read ``os.environ``. Use :func:`get_settings` in
application code and :func:`load_settings` in tests that need a fresh load.
The API, crawler and provider knobs are nested sections of this one module;
their legacy ``UNI_RAG_<SECTION>_<FIELD>`` environment names are still read,
so no deployment has to rename a variable during the fold (ADR 0008).
"""

import json
import os
from collections.abc import Mapping
from functools import lru_cache
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from uni_rag_core.errors import ConfigError


class ApiSection(BaseModel):
    """HTTP-surface settings folded from G's former local module."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str = "v1"
    log_level: str = "INFO"
    auth_enabled: bool = False
    api_key: str = "local-dev-key"
    rate_limit_capacity: int = Field(default=30, gt=0)
    rate_limit_refill_per_second: float = Field(default=1.0, gt=0)
    rate_limit_exempt_paths: tuple[str, ...] = (
        "/health/live",
        "/health/ready",
        "/openapi.json",
        "/docs",
        "/redoc",
    )
    max_top_k: int = Field(default=20, gt=0)
    trace_header: str = "X-Trace-Id"
    trace_header_enabled: bool = True


class CrawlerSection(BaseModel):
    """Crawler knobs folded from A's former domain-local ``CrawlerConfig``."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seeds: tuple[str, ...] = ()
    max_depth: int = Field(default=2, ge=0)
    requests_per_second: float = Field(default=1.0, gt=0)
    user_agent: str = "uni-rag-crawler/0.1 (+https://example.invalid/bot)"

    @field_validator("seeds")
    @classmethod
    def _validate_seeds(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject any configured seed that is not an HTTP(S) URL."""
        for seed in value:
            if not seed.startswith(("http://", "https://")):
                msg = "crawler seeds must be HTTP(S) URLs"
                raise ValueError(msg)
        return value

    @field_validator("user_agent")
    @classmethod
    def _validate_user_agent(cls, value: str) -> str:
        """Keep the crawler identifiable: a blank agent is never valid."""
        if not value.strip():
            msg = "user_agent must not be blank"
            raise ValueError(msg)
        return value


class ProvidersSection(BaseModel):
    """Live-provider opt-in promised by ADR 0002; off by default, never in CI."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    live_enabled: bool = False
    google_api_key: SecretStr | None = None
    openai_api_key: SecretStr | None = None


SECTION_ENV_PREFIXES: Mapping[str, str] = {
    "api": "UNI_RAG_API_",
    "crawler": "UNI_RAG_CRAWLER_",
    "providers": "UNI_RAG_PROVIDERS_",
}

_SECTION_TYPES: dict[str, type[BaseModel]] = {
    "api": ApiSection,
    "crawler": CrawlerSection,
    "providers": ProvidersSection,
}


def _legacy_section_env(section: str) -> dict[str, Any]:
    """Read ``UNI_RAG_<SECTION>_<FIELD>`` for one nested section.

    Complex fields (tuples, lists) accept a JSON value, mirroring
    pydantic-settings' own env decoding for non-scalar fields.
    """
    prefix = SECTION_ENV_PREFIXES[section]
    values: dict[str, Any] = {}
    for name, field in _SECTION_TYPES[section].model_fields.items():
        raw = os.environ.get(f"{prefix}{name.upper()}")
        if raw is None:
            continue
        if field.annotation in (str, int, float, bool):
            values[name] = raw
        else:
            try:
                values[name] = json.loads(raw)
            except (TypeError, ValueError):
                values[name] = raw
    return values


class Settings(BaseSettings):
    """Validated application settings."""

    model_config = SettingsConfigDict(
        env_prefix="UNI_RAG_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    app_name: str = "uni-rag"
    environment: str = "local"
    log_level: str = "INFO"

    # Required: foundation fails fast if these are absent (L8).
    qdrant_url: str
    postgres_dsn: str
    minio_endpoint: str

    # Optional infrastructure / tuning. The MinIO credential defaults are
    # dev-only placeholders; deployments must override both UNI_RAG_MINIO_*
    # variables rather than relying on them (see .env.example).
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "uni-rag"
    langfuse_host: str | None = None
    embedding_dimension: int = Field(default=16, gt=0)
    default_top_k: int = Field(default=10, gt=0)
    abstention_threshold: float = Field(default=0.35, ge=0.0, le=1.0)

    api: ApiSection = ApiSection()
    crawler: CrawlerSection = CrawlerSection()
    providers: ProvidersSection = ProvidersSection()

    @model_validator(mode="before")
    @classmethod
    def _legacy_env_names(cls, values: Any) -> Any:
        """Accept the legacy flat env names for each nested section's fields."""
        if not isinstance(values, dict):
            return values
        data: dict[str, Any] = dict(values)
        for section in _SECTION_TYPES:
            current = data.get(section)
            if isinstance(current, BaseModel):
                supplied = dict(current)
            elif isinstance(current, Mapping):
                supplied = dict(current)
            elif current is None:
                supplied = {}
            else:
                continue
            for name, raw in _legacy_section_env(section).items():
                supplied.setdefault(name, raw)
            data[section] = supplied
        return data

    @field_validator("environment")
    @classmethod
    def _normalise_environment(cls, value: str) -> str:
        """Lower-case the environment name for the CI guard."""
        return value.strip().lower() or "local"

    def model_post_init(self, __context: Any) -> None:
        """Refuse live providers in CI; fakes remain the default (L4, ADR 0002)."""
        if self.providers.live_enabled and self.environment in {"ci", "test"}:
            msg = "live providers must stay off in CI"
            raise ValueError(msg)


def load_settings() -> Settings:
    """Load and validate settings, raising a clear :class:`ConfigError` on failure."""
    try:
        return Settings()
    except ValidationError as exc:
        missing = [str(error["loc"][0]) for error in exc.errors() if error["type"] == "missing"]
        detail = (
            f"Missing required settings: {', '.join(missing)}." if missing else "Invalid settings."
        )
        raise ConfigError(
            f"{detail} Set the corresponding UNI_RAG_* environment variables (see .env.example).",
            context={"errors": exc.errors()},
        ) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide cached settings instance."""
    return load_settings()
