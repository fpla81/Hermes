"""case artifact key

Revision ID: 0003_case_artifact_key
Revises: 0002_case_capture_fields
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0003_case_artifact_key"
down_revision = "0002_case_capture_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "cases", sa.Column("artifact_key", sa.String(length=512), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("cases", "artifact_key")
