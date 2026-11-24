"""initial documents, chunks and crawl state

Revision ID: 0001_initial
Revises:
Create Date: 2026-01-01

Soft-delete (``deleted_at``) and version columns are part of the baseline; no
schema change is ever applied by hand (working agreement, AGENT.md L1/L12).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the document, chunk-version and crawl-state tables."""
    op.create_table(
        "documents",
        sa.Column("doc_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("doc_type", sa.String(length=64), nullable=False),
        sa.Column("last_crawled", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("doc_id"),
    )
    op.create_index("ix_documents_doc_type", "documents", ["doc_type"], unique=False)
    op.create_index("ix_documents_live", "documents", ["deleted_at"], unique=False)

    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.String(length=255), nullable=False),
        sa.Column("doc_id", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("superseded_by", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["doc_id"], ["documents.doc_id"]),
        sa.PrimaryKeyConstraint("chunk_id", "version"),
    )
    op.create_index("ix_chunks_doc_id", "chunks", ["doc_id"], unique=False)
    op.create_index("ix_chunks_live", "chunks", ["deleted_at"], unique=False)
    op.create_index("ix_chunks_doc_live", "chunks", ["doc_id", "deleted_at"], unique=False)
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"], unique=False)

    op.create_table(
        "crawl_state",
        sa.Column("doc_id", sa.String(length=255), nullable=False),
        sa.Column("last_crawled", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("doc_id"),
    )


def downgrade() -> None:
    """Drop the baseline tables in reverse dependency order."""
    op.drop_table("crawl_state")
    op.drop_index("ix_chunks_content_hash", table_name="chunks")
    op.drop_index("ix_chunks_doc_live", table_name="chunks")
    op.drop_index("ix_chunks_live", table_name="chunks")
    op.drop_index("ix_chunks_doc_id", table_name="chunks")
    op.drop_table("chunks")
    op.drop_index("ix_documents_live", table_name="documents")
    op.drop_index("ix_documents_doc_type", table_name="documents")
    op.drop_table("documents")
