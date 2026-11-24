"""Canonical sample contracts shared by every test."""

from datetime import UTC, datetime

from uni_rag_core import (
    Answer,
    Chunk,
    Citation,
    DocType,
    Document,
    FetchResult,
    ImageRef,
    Language,
    PastPaperQuestion,
    Query,
    ScoredChunk,
    VectorHit,
)

FIXED_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def image_ref() -> ImageRef:
    return ImageRef(
        ref_id="images/doc-1/p1.png",
        source_url="https://example.edu/papers/2024.pdf",
        page=1,
        caption="Past paper page 1",
    )


def document() -> Document:
    return Document(
        doc_id="doc-1",
        source_url="https://example.edu/courses/cs101",
        title="CS-101 Course Outline",
        doc_type=DocType.WEB_PAGE,
        last_crawled=FIXED_TIME,
        content_hash="hash-doc-1",
        metadata={"faculty": "CS"},
    )


def chunk() -> Chunk:
    return Chunk(
        chunk_id="chunk-1",
        doc_id="doc-1",
        source_url="https://example.edu/courses/cs101",
        heading_path=["CS-101", "Assessment", "Midterm"],
        content_hash="hash-chunk-1",
        last_crawled=FIXED_TIME,
        doc_type=DocType.WEB_PAGE,
        version="1",
        text="The midterm exam contributes 40 percent to the final grade.",
        chunk_index=0,
        token_count=12,
        page=3,
        image_ref=image_ref(),
    )


def question() -> PastPaperQuestion:
    return PastPaperQuestion(
        question_id="q-1",
        doc_id="doc-paper",
        source_url="https://example.edu/papers/2024.pdf",
        page=1,
        question_number=1,
        text="Define a binary search tree.",
        year=2024,
        subject="CS-101",
        options=["A", "B", "C", "D"],
        image_ref=image_ref(),
    )


def query() -> Query:
    return Query(
        query_id="query-1",
        text="What is the weight of the midterm?",
        language=Language.EN,
        top_k=5,
        filters={"doc_type": "web_page"},
    )


def citation() -> Citation:
    return Citation(
        chunk_id="chunk-1",
        doc_id="doc-1",
        source_url="https://example.edu/courses/cs101",
        snippet="The midterm exam contributes 40 percent",
        page=3,
        score=0.91,
    )


def answer() -> Answer:
    return Answer(
        answer_id="answer-1",
        query_id="query-1",
        text="The midterm contributes 40 percent.",
        citations=[citation()],
        images=[image_ref()],
        abstained=False,
        confidence=0.91,
        language=Language.EN,
    )


def fetch_result() -> FetchResult:
    return FetchResult(
        url="https://example.edu/courses/cs101",
        final_url="https://example.edu/courses/cs101",
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=b"<html><body>hello</body></html>",
    )


def scored_chunk() -> ScoredChunk:
    return ScoredChunk(chunk=chunk(), score=0.75, rank=1)


def vector_hit() -> VectorHit:
    return VectorHit(chunk_id="chunk-1", score=0.75, payload=chunk().model_dump(mode="json"))


def all_models() -> list[object]:
    """Every schema instance that must round-trip through JSON losslessly."""
    return [
        image_ref(),
        document(),
        chunk(),
        question(),
        query(),
        citation(),
        answer(),
        fetch_result(),
        scored_chunk(),
        vector_hit(),
    ]
