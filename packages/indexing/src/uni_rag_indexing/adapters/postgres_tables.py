"""Single source of truth for the relational schema (L9/L12).

Both the adapter and the Alembic environment import this ``MetaData``, so a
drift between migration and domain protocols is caught by a test instead of
appearing in production. Column types stay portable so the baseline migration
can be verified on SQLite when compose is unavailable.
"""

from __future__ import annotations

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
)

metadata = MetaData()

documents = Table(
    "documents",
    metadata,
    Column("doc_id", String(255), primary_key=True),
    Column("source_url", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("doc_type", String(64), nullable=False),
    Column("last_crawled", DateTime(timezone=True), nullable=False),
    Column("content_hash", String(128), nullable=False),
    Column("version", String(64), nullable=False),
    Column("language", String(16), nullable=False),
    Column("metadata_json", JSON, nullable=False),
    Column("indexed_at", DateTime(timezone=True), nullable=False),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Index("ix_documents_doc_type", "doc_type"),
    Index("ix_documents_live", "deleted_at"),
)

chunks = Table(
    "chunks",
    metadata,
    Column("chunk_id", String(255), primary_key=True),
    Column("doc_id", String(255), ForeignKey("documents.doc_id"), nullable=False),
    Column("version", String(64), primary_key=True),
    Column("content_hash", String(128), nullable=False),
    Column("payload", JSON, nullable=False),
    Column("indexed_at", DateTime(timezone=True), nullable=False),
    Column("deleted_at", DateTime(timezone=True), nullable=True),
    Column("superseded_by", String(255), nullable=True),
    Index("ix_chunks_doc_id", "doc_id"),
    Index("ix_chunks_live", "deleted_at"),
    Index("ix_chunks_doc_live", "doc_id", "deleted_at"),
    Index("ix_chunks_content_hash", "content_hash"),
)

crawl_state = Table(
    "crawl_state",
    metadata,
    Column("doc_id", String(255), primary_key=True),
    Column("last_crawled", DateTime(timezone=True), nullable=False),
    Column("content_hash", String(128), nullable=False),
    Column("status", String(32), nullable=False),
    Column("attempts", Integer, nullable=False),
    Column("error", Text, nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

# ADR 0011: parsed PaperRecords, not raw crawl responses and not Chunks. Every
# provenance field is a column frozen at write time; only the ImageRef key is
# kept for the ObjectStore. Qdrant stays vector-only (ADR 0010).
parsed_paper_records = Table(
    "parsed_paper_records",
    metadata,
    Column("question_id", String(255), primary_key=True),
    Column("doc_id", String(255), nullable=False),
    Column("source_url", Text, nullable=False),
    Column("page", Integer, nullable=False),
    Column("question_number", Integer, nullable=False),
    Column("text", Text, nullable=False),
    Column("last_crawled", DateTime(timezone=True), nullable=False),
    Column("year", Integer, nullable=True),
    Column("subject", Text, nullable=True),
    Column("options_json", JSON, nullable=False),
    Column("image_ref_json", JSON, nullable=True),
    Column("course_code", String(64), nullable=True),
    Column("term", String(32), nullable=True),
    Column("exam_type", String(32), nullable=True),
    Column("department", Text, nullable=True),
    Column("ordinal", Integer, nullable=False),
    Column("indexed_at", DateTime(timezone=True), nullable=False),
    Index("ix_parsed_papers_ordinal", "ordinal"),
    Index("ix_parsed_papers_doc_id", "doc_id"),
    Index(
        "ix_parsed_papers_filters",
        "course_code",
        "year",
        "term",
        "exam_type",
        "department",
    ),
)

__all__ = ["chunks", "crawl_state", "documents", "metadata", "parsed_paper_records"]
