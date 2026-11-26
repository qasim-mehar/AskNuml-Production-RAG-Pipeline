"""parsed paper records (ADR 0011)

Revision ID: 0002_parsed_paper_records
Revises: 0001_initial
Create Date: 2026-11-26

Stores the parser's segmented ``PaperRecord`` with provenance frozen at write
time. No raw crawl response, no Chunk and no Qdrant point is added (ADR 0010).
Page images remain in ObjectStore; ``image_ref_json`` holds the resolvable key.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_parsed_paper_records"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the parsed-record table and its filter/order indexes."""
    op.create_table(
        "parsed_paper_records",
        sa.Column("question_id", sa.String(length=255), nullable=False),
        sa.Column("doc_id", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("question_number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("last_crawled", sa.DateTime(timezone=True), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("subject", sa.Text(), nullable=True),
        sa.Column("options_json", sa.JSON(), nullable=False),
        sa.Column("image_ref_json", sa.JSON(), nullable=True),
        sa.Column("course_code", sa.String(length=64), nullable=True),
        sa.Column("term", sa.String(length=32), nullable=True),
        sa.Column("exam_type", sa.String(length=32), nullable=True),
        sa.Column("department", sa.Text(), nullable=True),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("indexed_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("question_id"),
    )
    op.create_index("ix_parsed_papers_ordinal", "parsed_paper_records", ["ordinal"], unique=False)
    op.create_index("ix_parsed_papers_doc_id", "parsed_paper_records", ["doc_id"], unique=False)
    op.create_index(
        "ix_parsed_papers_filters",
        "parsed_paper_records",
        ["course_code", "year", "term", "exam_type", "department"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the parsed-record indexes and table."""
    op.drop_index("ix_parsed_papers_filters", table_name="parsed_paper_records")
    op.drop_index("ix_parsed_papers_doc_id", table_name="parsed_paper_records")
    op.drop_index("ix_parsed_papers_ordinal", table_name="parsed_paper_records")
    op.drop_table("parsed_paper_records")
