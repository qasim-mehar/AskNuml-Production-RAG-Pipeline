"""Ports (protocols) that every adapter must satisfy (L3)."""

from uni_rag_core.ports.clock import Clock
from uni_rag_core.ports.embedder import Embedder
from uni_rag_core.ports.fetcher import Fetcher
from uni_rag_core.ports.llm import LLM
from uni_rag_core.ports.object_store import ObjectStore
from uni_rag_core.ports.reranker import Reranker
from uni_rag_core.ports.vector_store import VectorStore

__all__ = [
    "Clock",
    "Embedder",
    "Fetcher",
    "LLM",
    "ObjectStore",
    "Reranker",
    "VectorStore",
]
