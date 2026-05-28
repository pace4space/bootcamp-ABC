"""Ex3 pipeline observability tables: raw_documents, extraction_runs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-28

These two tables are append-only observability stores.
They intentionally have NO foreign key back to candidates/positions —
a failed extraction that produces no entity still needs a log row.

errors and warnings use TEXT[] (Postgres-native).
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. raw_documents
    # ------------------------------------------------------------------
    op.create_table(
        "raw_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("format", sa.Text(), nullable=False),
        sa.Column("document_kind", sa.Text(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=False),
        sa.Column("char_count", sa.Integer(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="raw_documents_pkey"),
        sa.CheckConstraint(
            "format IN ('pdf', 'docx', 'txt')",
            name="raw_documents_format_check",
        ),
        sa.CheckConstraint(
            "document_kind IN ('cv', 'position')",
            name="raw_documents_kind_check",
        ),
    )

    # ------------------------------------------------------------------
    # 2. extraction_runs
    # ------------------------------------------------------------------
    op.create_table(
        "extraction_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("raw_document_id", sa.Integer(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("raw_llm_output", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.Text(), nullable=True),
        sa.Column(
            "errors",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "warnings",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column(
            "input_tokens",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "output_tokens",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "latency_ms",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="extraction_runs_pkey"),
        sa.ForeignKeyConstraint(
            ["raw_document_id"],
            ["raw_documents.id"],
            name="extraction_runs_raw_document_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('success', 'partial', 'failed')",
            name="extraction_runs_status_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("extraction_runs")
    op.drop_table("raw_documents")
