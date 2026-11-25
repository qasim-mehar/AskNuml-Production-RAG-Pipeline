"""Test-only helpers for deterministic request bodies and SSE parsing."""

import json
from typing import Any

from uni_rag_api.composition import ephemeral_settings
from uni_rag_api.fixtures import QUERY_EN
from uni_rag_core import Answer, ApiSection, Language, Settings


def make_query(
    *,
    text: str = QUERY_EN,
    query_id: str = "query-en-001",
    language: Language | str = Language.EN,
    top_k: int = 5,
    filters: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build a Query JSON body that maps onto a fixture answer."""
    return {
        "query_id": query_id,
        "text": text,
        "language": language.value if isinstance(language, Language) else language,
        "top_k": top_k,
        "filters": filters if filters is not None else {"doc_type": "web_page"},
    }


def make_settings(**api_overrides: Any) -> Settings:
    """Build folded core settings with API-section overrides for a lane test."""
    return ephemeral_settings(api=ApiSection(**api_overrides))


def expected_body(answer: Answer) -> str:
    """Byte-stable JSON serialisation expected from the API."""
    return json.dumps(answer.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":"))


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse an SSE body into ordered ``(event, data)`` pairs."""
    events: list[tuple[str, dict[str, Any]]] = []
    for block in body.strip().split("\n\n"):
        event = ""
        data = ""
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: ") :]
            elif line.startswith("data: "):
                data = line[len("data: ") :]
        if not event or not data:
            msg = f"malformed SSE block: {block!r}"
            raise ValueError(msg)
        events.append((event, json.loads(data)))
    return events
