"""case capture fields

Revision ID: 0002_case_capture_fields
Revises: 0001_create_cases
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_case_capture_fields"
down_revision = "0001_create_cases"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("raw_html", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("last_error", sa.Text(), nullable=True))
    op.add_column(
        "cases", sa.Column("captured_at", sa.DateTime(timezone=False), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("cases", "captured_at")
    op.drop_column("cases", "last_error")
    op.drop_column("cases", "raw_html")
