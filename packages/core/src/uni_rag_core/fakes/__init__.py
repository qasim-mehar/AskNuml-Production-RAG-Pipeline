"""In-memory fakes for every port (L3, L4)."""

from uni_rag_core.fakes.clock import FakeClock, SystemClock
from uni_rag_core.fakes.embedder import FakeEmbedder
from uni_rag_core.fakes.fetcher import FakeFetcher
from uni_rag_core.fakes.llm import FakeLLM
from uni_rag_core.fakes.object_store import FakeObjectStore
from uni_rag_core.fakes.reranker import FakeReranker
from uni_rag_core.fakes.vector_store import FakeVectorStore

__all__ = [
    "FakeClock",
    "FakeEmbedder",
    "FakeFetcher",
    "FakeLLM",
    "FakeObjectStore",
    "FakeReranker",
    "FakeVectorStore",
    "SystemClock",
]
