"""Domain-local ports for the API (L3).

These are API boundaries, not core contracts: Lane E's real retrieval service
will implement :class:`AnswerService` at integration. Ports stay synchronous;
adapters may be async internally (AGENT.md §4).
"""

from collections.abc import Iterator, Mapping
from typing import Protocol, runtime_checkable

from uni_rag_core import Answer, Query


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


FakeCorpus = Mapping[str, Answer]
