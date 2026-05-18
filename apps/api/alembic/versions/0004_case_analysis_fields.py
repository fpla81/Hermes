"""case analysis fields

Revision ID: 0004_case_analysis_fields
Revises: 0003_case_artifact_key
Create Date: 2026-05-14
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0004_case_analysis_fields"
down_revision = "0003_case_artifact_key"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("analysis_result", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("anonymization_map", sa.JSON(), nullable=True))
    op.add_column(
        "cases", sa.Column("analyzed_at", sa.DateTime(timezone=False), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("cases", "analyzed_at")
    op.drop_column("cases", "anonymization_map")
    op.drop_column("cases", "analysis_result")
