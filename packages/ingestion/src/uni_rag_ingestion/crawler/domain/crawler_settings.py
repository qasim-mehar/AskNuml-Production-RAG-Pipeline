"""Typed crawler configuration (L8).

Core settings are frozen and Lane 0 owns them, so the crawler knobs live in
this domain-local typed model. The composition root supplies the values; the
handoff requests that they be folded into ``uni_rag_core.config.settings``
through a CONTRACT-CHANGE PR.
"""

from pydantic import BaseModel, ConfigDict, Field, field_validator

from uni_rag_core.errors import ValidationError as CoreValidationError
from uni_rag_ingestion.crawler.domain.frontier import canonicalize_url

DEFAULT_USER_AGENT = "uni-rag-crawler/0.1 (+https://example.invalid/bot)"


class CrawlerConfig(BaseModel):
    """Every crawl knob, validated once at the boundary (L8)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    seeds: tuple[str, ...]
    max_depth: int = Field(default=2, ge=0)
    requests_per_second: float = Field(default=1.0, gt=0)
    user_agent: str = Field(default=DEFAULT_USER_AGENT, min_length=1)

    @field_validator("seeds")
    @classmethod
    def _validate_seeds(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        """Reject an empty seed list and any non-HTTP(S) seed."""
        if not value:
            msg = "at least one seed URL is required"
            raise ValueError(msg)
        for seed in value:
            try:
                canonicalize_url(seed)
            except CoreValidationError as exc:
                raise ValueError(exc.message) from exc
        return value

    @field_validator("user_agent")
    @classmethod
    def _validate_user_agent(cls, value: str) -> str:
        """Reject a blank user agent so requests always identify the crawler."""
        if not value.strip():
            msg = "user_agent must not be blank"
            raise ValueError(msg)
        return value
