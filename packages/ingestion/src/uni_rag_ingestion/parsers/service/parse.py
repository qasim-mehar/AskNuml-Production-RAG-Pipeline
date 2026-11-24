"""Orchestration: parse, segment, extract, persist page images, emit records (L9)."""

from __future__ import annotations

from pathlib import Path

from uni_rag_core import Document, ImageRef, PastPaperQuestion
from uni_rag_core.errors import ParseError, StorageError
from uni_rag_core.logging import get_logger
from uni_rag_core.ports.object_store import ObjectStore
from uni_rag_ingestion.parsers.domain.metadata_extractor import extract_metadata
from uni_rag_ingestion.parsers.domain.models import (
    DocumentParser,
    ParsedPage,
    ParseOutcome,
    QuestionSpan,
    TableRecord,
)
from uni_rag_ingestion.parsers.domain.question_segmenter import segment_questions
from uni_rag_ingestion.parsers.domain.table_extractor import normalize_tables

_logger = get_logger("uni_rag.parsers.parse")

# Deterministic 1x1 PNG used only when no renderer can produce a page image.
# The caption on the resulting ImageRef says so explicitly (L13).
_PLACEHOLDER_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d4944415478da63fccfc0f01f00050001ffabce36890000000049454e44ae426082"
)


def _page_image(page: ParsedPage) -> tuple[bytes, str]:
    if page.image is not None:
        return page.image, "scanned past-paper page"
    return _PLACEHOLDER_PNG, "placeholder page image (no renderer available)"


def _cover_text(pages: tuple[ParsedPage, ...]) -> str:
    return pages[0].text if pages else ""


def _with_source(exc: ParseError, source_path: Path) -> ParseError:
    return ParseError(
        exc.message,
        context={**exc.context, "source_path": str(source_path)},
    )


def parse_document(
    document: Document,
    *,
    source_path: Path,
    parser: DocumentParser,
    object_store: ObjectStore,
) -> ParseOutcome:
    """Turn one source document into segmented questions and page references.

    Args:
        document: frozen source contract supplying provenance fields (L5, L6).
        source_path: checked-in fixture path read by ``parser``.
        parser: source parser selected by the caller.
        object_store: port used for every page image (L3).

    Raises:
        ParseError: on parse, metadata, segmentation, table or image failure;
            the source path is always attached to the error context (L11).
    """
    _logger.info("parse.started", doc_id=document.doc_id, source_path=str(source_path))

    try:
        parsed = parser.parse(source_path)
    except ParseError as exc:
        raise _with_source(exc, source_path) from exc
    except (OSError, UnicodeError, ValueError) as exc:
        raise ParseError(
            "could not read source document",
            context={"source_path": str(source_path)},
        ) from exc

    try:
        metadata = extract_metadata(_cover_text(parsed.pages))
    except ParseError as exc:
        raise _with_source(exc, source_path) from exc

    try:
        spans: tuple[QuestionSpan, ...] = segment_questions(parsed.pages)
        tables: tuple[TableRecord, ...] = normalize_tables(
            [table for page in parsed.pages for table in page.tables]
        )
    except ParseError as exc:
        raise _with_source(exc, source_path) from exc

    image_refs: dict[int, ImageRef] = {}
    for page in parsed.pages:
        image, caption = _page_image(page)
        key = f"parsed-images/{document.doc_id}/p{page.page}.png"
        try:
            stored_key = object_store.put(key, image, content_type="image/png")
        except StorageError as exc:
            raise ParseError(
                "could not persist page image",
                context={**exc.context, "source_path": str(source_path), "key": key},
            ) from exc
        image_refs[page.page] = ImageRef(
            ref_id=stored_key,
            source_url=document.source_url,
            page=page.page,
            caption=caption,
        )

    questions = tuple(
        PastPaperQuestion(
            question_id=f"{document.doc_id}:q{span.question_number:02d}",
            doc_id=document.doc_id,
            source_url=document.source_url,
            page=span.page,
            question_number=span.question_number,
            text=span.text,
            year=metadata.year,
            subject=metadata.course_code,
            options=list(span.options),
            image_ref=image_refs[span.page],
        )
        for span in spans
    )

    _logger.info(
        "parse.completed",
        doc_id=document.doc_id,
        source_path=str(source_path),
        questions=len(questions),
        pages=len(parsed.pages),
        tables=len(tables),
    )
    return ParseOutcome(
        questions=questions,
        metadata=metadata,
        tables=tables,
        image_refs=image_refs,
    )
