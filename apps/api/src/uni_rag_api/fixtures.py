"""Deterministic fixtures for the fake backend and the new HTTP routes (L3, L4).

Every answer here carries frozen core provenance fields (L5, L6). Lane E's real
retrieval service replaces the injected service at integration; the wire
contract does not change. Image bytes and their content types are fixed so the
image route can be tested without a live object store.
"""

from datetime import UTC, datetime

from uni_rag_api.ports import PaperRecord
from uni_rag_core import Answer, Citation, ImageRef, Language

QUERY_EN = "What is the weight of the midterm?"
QUERY_UR = "فائنل امتحان کا وزن کتنا ہے؟"
QUERY_ROMAN_UR = "final exam ka weight kya hai?"
QUERY_ABSTAIN = "What is the tuition fee for 2030?"
QUERY_IMAGE = "Show me the past paper page for CS-101"

_EN_CITATION = Citation(
    chunk_id="chunk-en-001",
    doc_id="doc-cs101",
    source_url="https://example.edu/courses/cs101/assessment",
    snippet="The midterm exam contributes 40 percent to the final grade.",
    page=3,
    score=0.91,
)
_EN_IMAGE = ImageRef(
    ref_id="images/cs101/midterm-p3.png",
    source_url="https://example.edu/courses/cs101/assessment",
    page=3,
    caption="Assessment table, page 3",
)

_UR_CITATION = Citation(
    chunk_id="chunk-ur-001",
    doc_id="doc-cs101-ur",
    source_url="https://example.edu/urdu/courses/cs101",
    snippet="درمیانی امتحان فائنل گریڈ کا 40 فیصد حصہ ہے۔",
    page=3,
    score=0.89,
)
_UR_IMAGE = ImageRef(
    ref_id="images/cs101/urdu-p3.png",
    source_url="https://example.edu/urdu/courses/cs101",
    page=3,
    caption="امتحانی جدول، صفحہ 3",
    mime_type="image/png",
)

_ROMAN_UR_CITATION = Citation(
    chunk_id="chunk-roman-001",
    doc_id="doc-cs101-roman",
    source_url="https://example.edu/roman-urdu/courses/cs101",
    snippet="Midterm exam final grade ka 40 percent hai.",
    page=3,
    score=0.88,
)

_IMAGE_CITATION = Citation(
    chunk_id="chunk-paper-001",
    doc_id="doc-paper-2024",
    source_url="https://example.edu/papers/2024.pdf",
    snippet="CS-101 past paper, question 1",
    page=1,
    score=0.94,
)
_IMAGE_REF = ImageRef(
    ref_id="images/papers/2024-p1.png",
    source_url="https://example.edu/papers/2024.pdf",
    page=1,
    caption="CS-101 past paper page 1",
)

EN_ANSWER = Answer(
    answer_id="answer-en-001",
    query_id="query-en-001",
    text="The midterm contributes 40 percent to the final grade.",
    citations=[_EN_CITATION],
    images=[_EN_IMAGE],
    abstained=False,
    confidence=0.91,
    language=Language.EN,
)

UR_ANSWER = Answer(
    answer_id="answer-ur-001",
    query_id="query-ur-001",
    text="درمیانی امتحان فائنل گریڈ کا 40 فیصد حصہ ہے۔",
    citations=[_UR_CITATION],
    images=[_UR_IMAGE],
    abstained=False,
    confidence=0.89,
    language=Language.UR,
)

ROMAN_UR_ANSWER = Answer(
    answer_id="answer-roman-001",
    query_id="query-roman-001",
    text="Midterm final grade ka 40 percent hai.",
    citations=[_ROMAN_UR_CITATION],
    images=[],
    abstained=False,
    confidence=0.88,
    language=Language.ROMAN_URDU,
)

ABSTAIN_ANSWER = Answer(
    answer_id="answer-abstain-001",
    query_id="query-abstain-001",
    text=(
        "I could not verify the 2030 tuition fee from any indexed source. "
        "Next step: check the official fee schedule at https://example.edu/fees "
        "or contact the registrar."
    ),
    citations=[],
    images=[],
    abstained=True,
    confidence=0.0,
    language=Language.EN,
)

IMAGE_ANSWER = Answer(
    answer_id="answer-image-001",
    query_id="query-image-001",
    text="The CS-101 past paper page is available with the citation below.",
    citations=[_IMAGE_CITATION],
    images=[_IMAGE_REF],
    abstained=False,
    confidence=0.94,
    language=Language.EN,
)

FALLBACK_ANSWER = Answer(
    answer_id="answer-fallback-001",
    query_id="query-fallback-001",
    text=(
        "I could not find cited evidence for that question. "
        "Next step: ask about an indexed course topic or browse https://example.edu/courses."
    ),
    citations=[],
    images=[],
    abstained=True,
    confidence=0.0,
    language=Language.EN,
)

CORPUS: dict[str, Answer] = {
    QUERY_EN: EN_ANSWER,
    QUERY_UR: UR_ANSWER,
    QUERY_ROMAN_UR: ROMAN_UR_ANSWER,
    QUERY_ABSTAIN: ABSTAIN_ANSWER,
    QUERY_IMAGE: IMAGE_ANSWER,
}

# ADR 0007 fields are frozen here so both backends can be checked for pass-through.
LAST_CRAWLED = datetime(2026, 1, 15, 9, 30, tzinfo=UTC)
REAL_BACKEND_ANSWER = Answer(
    answer_id="answer-real-001",
    query_id="query-real-001",
    text="The CS-101 past paper page is available with the citation below.",
    citations=[
        Citation(
            chunk_id="chunk-paper-001",
            doc_id="doc-paper-2024",
            source_url="https://example.edu/papers/2024.pdf",
            snippet="CS-101 past paper, question 1",
            page=1,
            score=0.94,
            last_crawled=LAST_CRAWLED,
        )
    ],
    images=[
        ImageRef(
            ref_id="images/papers/2024-p1.png",
            source_url="https://example.edu/papers/2024.pdf",
            page=1,
            caption="CS-101 past paper page 1",
            image_url="/api/images/images/papers/2024-p1.png",
        )
    ],
    abstained=False,
    confidence=0.94,
    language=Language.EN,
    next_step=None,
    abstention_reason=None,
)

# Past-paper finder fixtures (L4, L5, L7). Source URLs are the frozen values
# used by the answer/image fixtures above; page numbers and the image key are
# frozen here — the provider copies provenance and invents no URL or crawl time.
PAPER_RECORDS: tuple[PaperRecord, ...] = (
    PaperRecord(
        question_id="question-paper-2024-1",
        doc_id="doc-paper-2024",
        source_url=_IMAGE_CITATION.source_url,
        page=1,
        question_number=1,
        text="What is the time complexity of binary search?",
        year=2024,
        subject="Computer Science",
        options=["O(1)", "O(log n)", "O(n)"],
        image_ref=ImageRef(
            ref_id="images/papers/2024-p1.png",
            source_url=_IMAGE_CITATION.source_url,
            page=1,
            caption="CS-101 past paper page 1",
            image_url="/api/images/images/papers/2024-p1.png",
        ),
        course_code="CS-101",
        term="fall",
        exam_type="final",
        department="Computer Science",
        last_crawled=LAST_CRAWLED,
    ),
    PaperRecord(
        question_id="question-paper-2024-2",
        doc_id="doc-cs101-ur",
        source_url=_UR_CITATION.source_url,
        page=3,
        question_number=2,
        text="بائنری سرچ کی Time Complexity کیا ہے؟",
        year=2024,
        subject="کمپیوٹر سائنس",
        options=[],
        image_ref=None,
        course_code="CS-101",
        term="fall",
        exam_type="final",
        department="کمپیوٹر سائنس",
        last_crawled=LAST_CRAWLED,
    ),
    PaperRecord(
        question_id="question-paper-2023-7",
        doc_id="doc-cs101",
        source_url=_EN_CITATION.source_url,
        page=3,
        question_number=7,
        text="Define a binary search tree.",
        year=2023,
        subject="Computer Science",
        options=[],
        image_ref=None,
        course_code="CS-101",
        term="spring",
        exam_type="midterm",
        department="Computer Science",
        last_crawled=LAST_CRAWLED,
    ),
    PaperRecord(
        question_id="question-paper-2024-urdu-3",
        doc_id="doc-cs101-ur",
        source_url=_UR_CITATION.source_url,
        page=4,
        question_number=3,
        text="امتحان میں ایک سوال حل کریں۔",
        year=2024,
        subject="اردو",
        options=[],
        image_ref=None,
        course_code="اردو-101",
        term="fall",
        exam_type="final",
        department="کمپیوٹر سائنس",
        last_crawled=LAST_CRAWLED,
    ),
)

# Object-store contents for the fake image route. Keys mirror ImageRef.ref_id
# values; the Urdu key pins L7 round-tripping through the encoded path segment.
IMAGE_BYTES: dict[str, bytes] = {
    "images/papers/2024-p1.png": b"\x89PNG\r\n\x1a\n uni-rag fake CS-101 past paper page 1",
    "images/cs101/midterm-p3.png": b"\x89PNG\r\n\x1a\n uni-rag fake assessment table page 3",
    "images/urdu/صفحہ-3.png": b"\x89PNG\r\n\x1a\n" + "uni-rag fake اردو صفحہ 3".encode(),
}
IMAGE_CONTENT_TYPES: dict[str, str] = {key: "image/png" for key in IMAGE_BYTES}

__all__ = [
    "ABSTAIN_ANSWER",
    "CORPUS",
    "EN_ANSWER",
    "FALLBACK_ANSWER",
    "IMAGE_ANSWER",
    "IMAGE_BYTES",
    "IMAGE_CONTENT_TYPES",
    "LAST_CRAWLED",
    "PAPER_RECORDS",
    "QUERY_ABSTAIN",
    "QUERY_EN",
    "QUERY_IMAGE",
    "QUERY_ROMAN_UR",
    "QUERY_UR",
    "REAL_BACKEND_ANSWER",
    "ROMAN_UR_ANSWER",
    "UR_ANSWER",
]
