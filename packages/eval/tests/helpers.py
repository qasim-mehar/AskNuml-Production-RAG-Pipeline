"""Shared, deterministic test helpers for the evaluation package."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from uni_rag_core import Answer, Citation, Language, Query

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    """Read a JSON fixture from this package's fixtures directory."""
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


class StubRetriever:
    """A trivial ``RetrievalCallable`` with no ports, proving Protocol injection."""

    def __init__(self, answers: Mapping[str, Mapping[str, Any]]) -> None:
        self._answers = answers

    def __call__(self, query: Query) -> Answer:
        spec = self._answers[query.query_id]
        citations = tuple(
            Citation(
                chunk_id=chunk_id,
                doc_id="doc-synthetic",
                source_url="https://example.invalid/synthetic",
                snippet=snippet,
            )
            for chunk_id, snippet in zip(spec["cited_chunk_ids"], spec["snippets"], strict=True)
        )
        return Answer(
            answer_id=f"stub-ans-{query.query_id}",
            query_id=query.query_id,
            text="stub answer",
            citations=list(citations),
            abstained=bool(spec["abstained"]),
            language=query.language or Language.EN,
        )
