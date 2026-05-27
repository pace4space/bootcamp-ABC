"""Initial schema — all 11 tables.

Revision ID: 0001
Revises: (none — this is the root migration)
Create Date: 2026-05-27

Tables created in FK-safe order:
  1. users
  2. candidates
  3. positions
  4. candidate_skills
  5. candidate_experience       (highlights: TEXT[] — Postgres only)
  6. candidate_education
  7. candidate_certifications
  8. candidate_languages
  9. position_requirements
 10. applications

downgrade() drops them in reverse order.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. users
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="users_pkey"),
        sa.UniqueConstraint("email", name="users_email_key"),
        sa.CheckConstraint(
            "role IN ('admin', 'recruiter', 'viewer')",
            name="users_role_check",
        ),
    )

    # ------------------------------------------------------------------
    # 2. candidates
    # ------------------------------------------------------------------
    op.create_table(
        "candidates",
        sa.Column("id", sa.String(20), nullable=False),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("headline", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("city", sa.Text(), nullable=True),
        sa.Column("linkedin_url", sa.Text(), nullable=True),
        sa.Column("github_url", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("source_cv_filename", sa.Text(), nullable=True),
        sa.Column("source_cv_format", sa.Text(), nullable=True),
        sa.Column("source_cv_path", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="candidates_pkey"),
        sa.UniqueConstraint("email", name="candidates_email_key"),
        sa.CheckConstraint(
            "status IN ('Active', 'Archived')",
            name="candidates_status_check",
        ),
        sa.CheckConstraint(
            "source_cv_format IN ('pdf', 'docx')",
            name="candidates_source_cv_format_check",
        ),
    )

    # ------------------------------------------------------------------
    # 3. positions
    # ------------------------------------------------------------------
    op.create_table(
        "positions",
        sa.Column("id", sa.String(20), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("hiring_manager_email", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("seniority", sa.Text(), nullable=True),
        sa.Column("salary_range", sa.Text(), nullable=True),
        sa.Column("source_document_filename", sa.Text(), nullable=True),
        sa.Column("source_document_path", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="positions_pkey"),
        sa.CheckConstraint(
            "status IN ('Open', 'Closed')",
            name="positions_status_check",
        ),
    )

    # ------------------------------------------------------------------
    # 4. candidate_skills
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_skills",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="candidate_skills_pkey"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="candidate_skills_candidate_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # 5. candidate_experience
    # NOTE: highlights is TEXT[] — Postgres-specific via postgresql.ARRAY.
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_experience",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=True),
        sa.Column(
            "highlights",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="candidate_experience_pkey"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="candidate_experience_candidate_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # 6. candidate_education
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_education",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("degree", sa.Text(), nullable=False),
        sa.Column("institution", sa.Text(), nullable=False),
        sa.Column("start_year", sa.Integer(), nullable=False),
        sa.Column("end_year", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="candidate_education_pkey"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="candidate_education_candidate_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # 7. candidate_certifications
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_certifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="candidate_certifications_pkey"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="candidate_certifications_candidate_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # 8. candidate_languages
    # ------------------------------------------------------------------
    op.create_table(
        "candidate_languages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("proficiency", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="candidate_languages_pkey"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="candidate_languages_candidate_id_fkey",
            ondelete="CASCADE",
        ),
    )

    # ------------------------------------------------------------------
    # 9. position_requirements
    # ------------------------------------------------------------------
    op.create_table(
        "position_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("position_id", sa.String(20), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="position_requirements_pkey"),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            name="position_requirements_position_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "type IN ('must_have', 'nice_to_have')",
            name="position_requirements_type_check",
        ),
    )

    # ------------------------------------------------------------------
    # 10. applications
    # ------------------------------------------------------------------
    op.create_table(
        "applications",
        sa.Column("id", sa.String(50), nullable=False),
        sa.Column("candidate_id", sa.String(20), nullable=False),
        sa.Column("position_id", sa.String(20), nullable=False),
        sa.Column("status", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id", name="applications_pkey"),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidates.id"],
            name="applications_candidate_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["positions.id"],
            name="applications_position_id_fkey",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('Waiting', 'Rejected', 'Screening', 'Offer', 'Hired')",
            name="applications_status_check",
        ),
        sa.UniqueConstraint(
            "candidate_id",
            "position_id",
            name="applications_candidate_position_uniq",
        ),
    )


def downgrade() -> None:
    # Drop in reverse FK order (dependents first, parents last).
    op.drop_table("applications")
    op.drop_table("position_requirements")
    op.drop_table("candidate_languages")
    op.drop_table("candidate_certifications")
    op.drop_table("candidate_education")
    op.drop_table("candidate_experience")
    op.drop_table("candidate_skills")
    op.drop_table("positions")
    op.drop_table("candidates")
    op.drop_table("users")
