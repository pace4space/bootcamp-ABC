"""Ex5 semantic search: candidate_embeddings and position_embeddings tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-01

Two dedicated 1:1 embedding tables with FK ON DELETE CASCADE.
The vector extension is created here (PostgreSQL only); already present in
pgvector/pgvector:pg16 image, but CREATE EXTENSION IF NOT EXISTS is idempotent.

No ANN index at this scale — exact cosine via sequential scan is sub-ms.
When N > ~10k rows add:
  CREATE INDEX ON candidate_embeddings USING hnsw (embedding vector_cosine_ops);
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "candidate_embeddings",
        sa.Column(
            "candidate_id",
            sa.String(20),
            sa.ForeignKey("candidates.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )

    op.create_table(
        "position_embeddings",
        sa.Column(
            "position_id",
            sa.String(20),
            sa.ForeignKey("positions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("embedding", Vector(512), nullable=False),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding_model", sa.Text(), nullable=False),
        sa.Column("text_sha256", sa.String(64), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("position_embeddings")
    op.drop_table("candidate_embeddings")
    # leave the vector extension in place — dropping it could break other objects
