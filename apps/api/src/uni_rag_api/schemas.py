"""Wire schemas: frozen core models re-exported, plus API-local envelopes.

No core schema is redefined here (L14). API-local models only frame transport
concerns — errors, probes and SSE events — and never alter Answer provenance.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from uni_rag_api.ports import PaperRecord
from uni_rag_core import Answer, Citation, ImageRef, Language, Query


class ErrorBody(BaseModel):
    """Machine-readable error envelope for every non-2xx response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class LiveStatus(BaseModel):
    """Liveness response: no dependency checks."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ok"]
    service: str


class ReadyStatus(BaseModel):
    """Readiness response: injected ports were checked."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: Literal["ready"]
    service: str


class FeedbackRequest(BaseModel):
    """ADR 0009 local-only feedback payload; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_id: str
    sentiment: Literal["positive", "negative"]
    reason: str | None = None
    query_id: str | None = None


class PaperSearchResult(BaseModel):
    """Finder response; the ``results`` key matches Lane H's strict mirror."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    results: list[PaperRecord]


class TokenEvent(BaseModel):
    """One ordered SSE token payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str


class CitationsEvent(BaseModel):
    """Final SSE event carrying the full cited answer (L5, L6)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer: Answer


__all__ = [
    "Answer",
    "Citation",
    "CitationsEvent",
    "ErrorBody",
    "FeedbackRequest",
    "ImageRef",
    "Language",
    "LiveStatus",
    "PaperRecord",
    "PaperSearchResult",
    "Query",
    "ReadyStatus",
    "TokenEvent",
]
