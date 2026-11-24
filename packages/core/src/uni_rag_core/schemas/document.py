"""Source document contract."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from uni_rag_core.schemas.enums import DocType, Language


class Document(BaseModel):
    """A fetched source document before chunking."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    source_url: str
    title: str
    doc_type: DocType
    last_crawled: datetime
    content_hash: str
    version: str = "1"
    language: Language = Language.EN
    metadata: dict[str, str] = Field(default_factory=dict)
