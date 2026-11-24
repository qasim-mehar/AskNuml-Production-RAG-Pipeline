"""The single typed settings module (L8).

No other module may read ``os.environ``. Use :func:`get_settings` in
application code and :func:`load_settings` in tests that need a fresh load.
"""

from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from uni_rag_core.errors import ConfigError


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
