"""Integration-level ADR-0007 provenance join (L5, L13).

Lane E's migration to the optional ``Citation.last_crawled`` / ``Answer.next_step``
fields is still pending. The integration layer joins those values from the
indexed chunks instead of string-parsing the answer footer. No lane code is
modified and no fact is invented: every value comes from a crawled document.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from uni_rag_core import Answer, Language
from uni_rag_core.schemas import Chunk

_NEXT_STEP: dict[Language, str] = {
    Language.EN: "Ask the university office or re-crawl the source for this fact.",
    Language.UR: "یہ معلومات یونیورسٹی دفتر سے پوچھیں یا ماخذ دوبارہ کرawl کریں۔",
    Language.ROMAN_URDU: "Yeh maloomat university office se poochen ya source ko dobara crawl karein.",
}
_REASON: dict[Language, str] = {
    Language.EN: "no crawled fixture supports an answer",
    Language.UR: "کرawl شدہ ماخذ میں جواب کے لیے ثبوت نہیں",
    Language.ROMAN_URDU: "crawled source mein jawab ka koi saboot nahi",
}


def attach_provenance(
    answer: Answer,
    chunks: Mapping[str, Chunk] | Iterable[Chunk],
    language: Language,
) -> Answer:
    """Attach ``last_crawled`` to citations and a next step to abstentions."""
    by_id = {
        chunk.chunk_id: chunk
        for chunk in (chunks.values() if isinstance(chunks, Mapping) else chunks)
    }
    citations = tuple(
        citation.model_copy(
            update={
                "last_crawled": by_id[citation.chunk_id].last_crawled
                if citation.chunk_id in by_id
                else citation.last_crawled
            }
        )
        for citation in answer.citations
    )
    update: dict[str, object] = {"citations": list(citations)}
    if answer.abstained:
        update.setdefault("next_step", answer.next_step or _NEXT_STEP[language])
        update.setdefault("abstention_reason", answer.abstention_reason or _REASON[language])
    return answer.model_copy(update=update)
