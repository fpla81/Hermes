"""create cases table

Revision ID: 0001_create_cases
Revises:
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0001_create_cases"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    case_status = sa.Enum(
        "draft",
        "capturing",
        "captured",
        "analyzing",
        "ready",
        "error",
        name="case_status",
    )
    case_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "cases",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("numero_processo", sa.String(length=64), nullable=False),
        sa.Column("titulo", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum(name="case_status", create_type=False),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_cases_user_id", "cases", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_cases_user_id", table_name="cases")
    op.drop_table("cases")
    sa.Enum(name="case_status").drop(op.get_bind(), checkfirst=True)
