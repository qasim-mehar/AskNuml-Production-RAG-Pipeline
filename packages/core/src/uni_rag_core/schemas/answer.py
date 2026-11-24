"""Answer and citation contracts (L5 provenance, L13 abstention)."""

from pydantic import BaseModel, ConfigDict, Field

from uni_rag_core.schemas.chunk import ImageRef
from uni_rag_core.schemas.enums import Language


class Citation(BaseModel):
    """A pointer from an answer span back to an indexed chunk."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    doc_id: str
    source_url: str
    snippet: str
    page: int | None = None
    score: float | None = None


class Answer(BaseModel):
    """A cited answer; ``abstained`` is True when evidence is insufficient."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    answer_id: str
    query_id: str
    text: str
    citations: list[Citation] = Field(default_factory=list)
    images: list[ImageRef] = Field(default_factory=list)
    abstained: bool = False
    confidence: float = 0.0
    language: Language = Language.EN
