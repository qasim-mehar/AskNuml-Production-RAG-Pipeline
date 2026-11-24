"""Incoming query contract."""

from pydantic import BaseModel, ConfigDict, Field

from uni_rag_core.schemas.enums import Language


class Query(BaseModel):
    """A student question (English, Urdu, or Roman Urdu)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    query_id: str
    text: str
    language: Language
    top_k: int = 10
    filters: dict[str, str] = Field(default_factory=dict)
