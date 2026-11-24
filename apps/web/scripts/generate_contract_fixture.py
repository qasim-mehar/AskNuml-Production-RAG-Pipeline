"""Regenerate the core-emitted contract fixture from the frozen Pydantic models.

Run from the repository root:
    uv run python apps/web/scripts/generate_contract_fixture.py

The Vitest contract suite parses this file with the TypeScript Zod mirrors, so
mirror fidelity is measured against real core output rather than a hand-written
copy (L1). This is a development-time generator; tests never import Python.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "packages" / "core" / "src"))

from uni_rag_core.schemas.answer import Answer, Citation  # noqa: E402
from uni_rag_core.schemas.chunk import ImageRef  # noqa: E402
from uni_rag_core.schemas.enums import Language  # noqa: E402
from uni_rag_core.schemas.past_paper import PastPaperQuestion  # noqa: E402
from uni_rag_core.schemas.query import Query  # noqa: E402

OUTPUT = REPO_ROOT / "apps" / "web" / "src" / "lib" / "api" / "mocks" / "core-emitted.json"


def main() -> None:
    """Emit representative core model dumps as pretty JSON for the web mirror tests."""
    query = Query(
        query_id="q-contract",
        text="What is the fee?",
        language=Language.EN,
        top_k=5,
        filters={"department": "CS"},
    )
    citation = Citation(
        chunk_id="c-1",
        doc_id="d-1",
        source_url="https://uni.example/fees",
        snippet="Fee is 1000",
        page=3,
        score=0.91,
    )
    image = ImageRef(
        ref_id="img-1",
        source_url="https://uni.example/past/2024",
        page=2,
        caption="Past paper page 2",
    )
    answer = Answer(
        answer_id="a-contract",
        query_id="q-contract",
        text="The fee is 1000.",
        citations=[citation],
        images=[image],
        abstained=False,
        confidence=0.91,
        language=Language.EN,
    )
    paper = PastPaperQuestion(
        question_id="pp-1",
        doc_id="d-pp",
        source_url="https://uni.example/past/2024",
        page=1,
        question_number=4,
        text="What is 2+2?",
        year=2024,
        subject="CS",
        options=["3", "4"],
        image_ref=image,
    )
    abstained = Answer(
        answer_id="a-abstain",
        query_id="q-contract",
        text="Insufficient evidence; try a more specific question.",
        abstained=True,
        confidence=0.0,
        language=Language.UR,
    )
    payload = {
        "query": json.loads(query.model_dump_json()),
        "citation": json.loads(citation.model_dump_json()),
        "image_ref": json.loads(image.model_dump_json()),
        "answer": json.loads(answer.model_dump_json()),
        "past_paper": json.loads(paper.model_dump_json()),
        "abstained_answer": json.loads(abstained.model_dump_json()),
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
