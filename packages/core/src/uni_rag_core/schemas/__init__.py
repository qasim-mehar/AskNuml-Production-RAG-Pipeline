"""Frozen data contracts. Import from here, never from individual modules."""

from uni_rag_core.schemas.answer import Answer, Citation
from uni_rag_core.schemas.chunk import Chunk, ImageRef, PayloadValue, ScoredChunk, VectorHit
from uni_rag_core.schemas.document import Document
from uni_rag_core.schemas.enums import DocType, Language
from uni_rag_core.schemas.fetch import FetchResult
from uni_rag_core.schemas.past_paper import PastPaperQuestion
from uni_rag_core.schemas.query import Query

__all__ = [
    "Answer",
    "Citation",
    "Chunk",
    "DocType",
    "Document",
    "FetchResult",
    "ImageRef",
    "Language",
    "PastPaperQuestion",
    "PayloadValue",
    "Query",
    "ScoredChunk",
    "VectorHit",
]
