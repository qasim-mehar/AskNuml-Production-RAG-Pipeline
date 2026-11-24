"""Pure parsing domain. No adapters or I/O are imported here (L2, L9)."""

from uni_rag_ingestion.parsers.domain.accuracy import (
    AccuracyReport,
    FixtureScore,
    MetadataScore,
    SegmentationScore,
    count_matched_questions,
    make_fixture_score,
    make_report,
    score_metadata_fields,
)
from uni_rag_ingestion.parsers.domain.metadata_extractor import extract_metadata
from uni_rag_ingestion.parsers.domain.models import (
    DocumentParser,
    PaperMetadata,
    ParsedDocument,
    ParsedPage,
    ParsedTable,
    ParseOutcome,
    QuestionSpan,
    TableRecord,
)
from uni_rag_ingestion.parsers.domain.question_segmenter import segment_questions
from uni_rag_ingestion.parsers.domain.table_extractor import normalize_tables

__all__ = [
    "AccuracyReport",
    "DocumentParser",
    "FixtureScore",
    "MetadataScore",
    "ParseOutcome",
    "PaperMetadata",
    "ParsedDocument",
    "ParsedPage",
    "ParsedTable",
    "QuestionSpan",
    "SegmentationScore",
    "TableRecord",
    "count_matched_questions",
    "extract_metadata",
    "make_fixture_score",
    "make_report",
    "normalize_tables",
    "score_metadata_fields",
    "segment_questions",
]
