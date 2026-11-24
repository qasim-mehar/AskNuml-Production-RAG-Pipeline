"""Domain-local ports for the API (L3).

These are API boundaries, not core contracts: Lane E's real retrieval service
will implement :class:`AnswerService` at integration. Ports stay synchronous;
adapters may be async internally (AGENT.md §4).
"""

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from uni_rag_core import Answer, ObjectStore, Query


@runtime_checkable
class AnswerService(Protocol):
    """Produces cited answers and their ordered text tokens."""

    def answer(self, query: Query) -> Answer:
        """Return a cited (or explicitly abstaining) answer for ``query``."""
        ...

    def tokens(self, answer: Answer) -> Iterator[str]:
        """Yield answer text tokens that join back to ``answer.text`` exactly."""
        ...


@runtime_checkable
class HealthProbe(Protocol):
    """Reports whether the injected dependencies are ready."""

    def is_ready(self) -> bool:
        """Return True when downstream dependencies are available."""
        ...


@runtime_checkable
class TypedObjectStore(ObjectStore, Protocol):
    """ObjectStore that can report a stored object's content type (ADR 0007)."""

    def content_type_of(self, key: str) -> str:
        """Return the content type recorded for ``key``."""
        ...


@dataclass(frozen=True)
class StoredImage:
    """Bytes and content type resolved from an object-store entry."""

    data: bytes
    content_type: str


@runtime_checkable
class ImageService(Protocol):
    """Synchronous image lookup used by the HTTP image route (L3)."""

    def get(self, ref_id: str) -> StoredImage:
        """Return stored bytes and their content type, or raise core NotFoundError."""
        ...


FakeCorpus = Mapping[str, Answer]
