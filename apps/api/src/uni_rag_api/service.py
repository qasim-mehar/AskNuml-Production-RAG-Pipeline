"""Deterministic fake answer service (L3, L4, L5).

The service owns answer orchestration; routers only route and serialise (L9).
No network, model or clock call happens here.
"""

from collections.abc import Iterator, Mapping

from uni_rag_api.fixtures import CORPUS, FALLBACK_ANSWER
from uni_rag_api.ports import AnswerService, FakeCorpus, HealthProbe
from uni_rag_core import Answer, Query


class FakeAnswerService:
    """Returns fixture answers, stamping only the request's ``query_id``.

    Citations, images and every provenance field are copied verbatim; the
    service never invents or strips them (L5, L6).
    """

    def __init__(self, corpus: FakeCorpus | None = None) -> None:
        self._corpus: Mapping[str, Answer] = dict(corpus if corpus is not None else CORPUS)

    def answer(self, query: Query) -> Answer:
        """Return the fixture answer for ``query.text``, or an abstaining fallback."""
        base = self._corpus.get(query.text.strip(), FALLBACK_ANSWER)
        return base.model_copy(update={"query_id": query.query_id})

    def tokens(self, answer: Answer) -> Iterator[str]:
        """Yield space-delimited tokens; ``" ".join(tokens) == answer.text``."""
        yield from answer.text.split(" ")


class FakeHealthProbe:
    """Fake readiness signal, flippable in tests without touching real ports."""

    def __init__(self, ready: bool = True) -> None:
        self.ready = ready

    def is_ready(self) -> bool:
        """Return the configured readiness value."""
        return self.ready


__all__ = ["FakeAnswerService", "FakeHealthProbe", "AnswerService", "HealthProbe"]
