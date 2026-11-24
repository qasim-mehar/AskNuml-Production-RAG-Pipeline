"""API-specific typed settings (L8).

The frozen core settings module owns infrastructure knobs; this module owns the
HTTP knobs this lane adds. The two use distinct environment prefixes so neither
lane can silently override the other. Folding these fields into
``uni_rag_core.config.settings.Settings`` is a Lane 0 CONTRACT-CHANGE request
recorded in the handoff — this lane does not patch core (L14).
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """Validated configuration for the HTTP surface only."""

    model_config = SettingsConfigDict(
        env_prefix="UNI_RAG_API_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    api_version: str = "v1"
    log_level: str = "INFO"

    # Auth stub: a single configured key compared in constant time. Anything
    # beyond this (OIDC, key rotation, scopes) is parked for a later milestone.
    auth_enabled: bool = False
    api_key: str = "local-dev-key"

    # In-memory token bucket. A settings-driven capacity and refill make the
    # limiter deterministic under tests that inject a controllable Clock.
    rate_limit_capacity: int = Field(default=30, gt=0)
    rate_limit_refill_per_second: float = Field(default=1.0, gt=0)
    rate_limit_exempt_paths: tuple[str, ...] = (
        "/health/live",
        "/health/ready",
        "/openapi.json",
        "/docs",
        "/redoc",
    )

    # Caller-supplied top_k is bounded by this typed knob rather than a literal.
    max_top_k: int = Field(default=20, gt=0)

    trace_header: str = "X-Trace-Id"
