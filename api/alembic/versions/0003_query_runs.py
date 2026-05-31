"""Ex4 SQL-RAG observability table: query_runs.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-31

Append-only log of every chat turn: question, generated SQL, prompt, model, tokens, status.
No FK to candidates/positions — a failed/unsafe query that produced no rows still needs a row.
No ARRAY columns (columns list is JSON-in-TEXT) so the same DDL runs on SQLite.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "query_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("generated_sql", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("model_id", sa.Text(), nullable=False),
        sa.Column("row_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("columns_json", sa.Text(), server_default=sa.text("'[]'"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("latency_ms", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id", name="query_runs_pkey"),
        sa.CheckConstraint(
            "status IN ('success', 'unsafe', 'sql_error', 'llm_error')",
            name="query_runs_status_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("query_runs")
