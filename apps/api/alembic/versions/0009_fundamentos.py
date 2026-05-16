"""fundamentos jurídicos por tema (RAG-like, keyword search)

Revision ID: 0009_fundamentos
Revises: 0008_case_parties
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_fundamentos"
down_revision = "0008_case_parties"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fundamentos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False, index=True),
        sa.Column("tema", sa.String(255), nullable=False),
        sa.Column("titulo", sa.String(255), nullable=False),
        sa.Column("corpo_md", sa.Text(), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=True),
        sa.Column("resumo", sa.Text(), nullable=True),
        sa.Column(
            "source_case_id",
            sa.Uuid(),
            sa.ForeignKey("cases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_fundamentos_user_tema",
        "fundamentos",
        ["user_id", "tema"],
    )


def downgrade() -> None:
    op.drop_index("ix_fundamentos_user_tema", table_name="fundamentos")
    op.drop_table("fundamentos")
