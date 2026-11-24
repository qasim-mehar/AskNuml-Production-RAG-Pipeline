"""Fixture-first oracle data for chunking (L12).

Expected chunk sets are written down here as explicit assertions' inputs before
any splitter runs. ``filler(n)`` yields exactly ``n`` four-letter tokens so the
token estimate is exactly ``n`` and the 300-500 band is checkable by hand.
"""

from __future__ import annotations

from datetime import UTC, datetime

from uni_rag_core.schemas.chunk import ImageRef
from uni_rag_core.schemas.document import Document
from uni_rag_core.schemas.enums import DocType, Language
from uni_rag_ingestion.chunking.domain.model import Block, BlockKind, ParsedDocument

CRAWLED = datetime(2026, 11, 24, 12, 0, 0, tzinfo=UTC)
_FILLER = ("abcd", "efgh", "ijkl", "mnop")
URDU_SENTENCE = "یہ ایک طویل اردو پیراگراف ہے جو چنکنگ کے دوران محفوظ رہنا چاہیے"


def filler(n: int) -> str:
    """Deterministic text of exactly ``n`` four-letter tokens."""
    return " ".join(_FILLER[i % len(_FILLER)] for i in range(n))


def document(
    *,
    doc_id: str = "doc-outline",
    doc_type: DocType = DocType.WEB_PAGE,
    language: Language = Language.EN,
) -> Document:
    """A frozen provenance record with no clock or random values."""
    return Document(
        doc_id=doc_id,
        source_url=f"https://example.edu.pk/{doc_id}",
        title="Fixture document",
        doc_type=doc_type,
        last_crawled=CRAWLED,
        content_hash="f" * 64,
        version="7",
        language=language,
    )


def _h(index: int, text: str, level: int) -> Block:
    return Block(kind=BlockKind.HEADING, text=text, index=index, level=level)


def _p(index: int, text: str) -> Block:
    return Block(kind=BlockKind.PARAGRAPH, text=text, index=index)


def heading_document() -> ParsedDocument:
    """Nested headings, four timed sections and one table (course-page shape)."""
    blocks = (
        _h(0, "Course Outline", 1),
        _h(1, "Course Information", 2),
        _p(2, filler(400)),
        Block(
            kind=BlockKind.TABLE,
            text="",
            index=3,
            table_rows=(
                ("Field", "Detail"),
                ("Instructor", "Dr. Ayesha Khan"),
                ("Credits", "4"),
                ("Semester", "Fall 2026"),
            ),
        ),
        _h(4, "Learning Outcomes", 2),
        _p(5, filler(450)),
        _h(6, "Assessment", 3),
        _p(7, filler(380)),
        _h(8, "Long Section", 2),
        _p(9, filler(900)),
    )
    return ParsedDocument(document(), blocks)


def table_document() -> ParsedDocument:
    """A table between two paragraphs: it must stay whole and in order."""
    blocks = (
        _h(0, "Course Information", 1),
        _p(1, filler(400)),
        Block(
            kind=BlockKind.TABLE,
            text="",
            index=2,
            table_rows=(
                ("Field", "Detail"),
                ("Instructor", "Dr. Ayesha Khan"),
                ("Credits", "4"),
                ("Semester", "Fall 2026"),
            ),
        ),
        _p(3, filler(400)),
    )
    return ParsedDocument(document(doc_id="doc-course-info"), blocks)


def sentence_document() -> ParsedDocument:
    """Four 225-token sentences: sentence boundaries differ from fixed windows."""
    sentences = [f"{filler(225)}." for _ in range(4)]
    blocks = (
        _h(0, "Course Outline", 1),
        _h(1, "Sentence Section", 2),
        _p(2, " ".join(sentences)),
    )
    return ParsedDocument(document(doc_id="doc-sentences"), blocks)


def urdu_document() -> ParsedDocument:
    """A long Urdu passage with Urdu full stops (L7)."""
    text = "۔ ".join([URDU_SENTENCE] * 100)
    blocks = (_h(0, "اردو کورس", 1), _p(1, text))
    return ParsedDocument(document(doc_id="doc-urdu", language=Language.UR), blocks)


def past_paper_document() -> ParsedDocument:
    """Three past-paper questions, each with a page and image reference."""
    source = "https://archive.example.edu.pk/past/2026.pdf"
    questions: list[Block] = []
    for number in (1, 2, 3):
        questions.append(
            Block(
                kind=BlockKind.QUESTION,
                text=f"Q{number} {filler(400)}",
                index=number,
                page=1,
                image_ref=ImageRef(
                    ref_id=f"page-1-q{number}",
                    source_url=source,
                    page=1,
                    caption=f"Question {number}",
                ),
            )
        )
    blocks = (
        _h(0, "Past Paper 2026", 1),
        *questions,
    )
    doc = document(
        doc_id="doc-past-paper",
        doc_type=DocType.PAST_PAPER,
        language=Language.UR,
    )
    return ParsedDocument(doc, tuple(blocks))


# Expected chunk sets (the oracle).
HEADING_EXPECTED_COUNT = 6
HEADING_EXPECTED_PATHS = (
    ["Course Outline", "Course Information"],
    ["Course Outline", "Course Information"],
    ["Course Outline", "Learning Outcomes"],
    ["Course Outline", "Learning Outcomes", "Assessment"],
    ["Course Outline", "Long Section"],
    ["Course Outline", "Long Section"],
)
TABLE_EXPECTED_COUNT = 3
TABLE_EXPECTED_CELLS = ("Dr. Ayesha Khan", "Credits | 4", "Semester | Fall 2026")
SENTENCE_EXPECTED_COUNT = 2
URDU_EXPECTED_WORDS = tuple("۔ ".join([URDU_SENTENCE] * 100).split())
PAST_PAPER_EXPECTED = (
    ("Q1", "page-1-q1"),
    ("Q2", "page-1-q2"),
    ("Q3", "page-1-q3"),
)
