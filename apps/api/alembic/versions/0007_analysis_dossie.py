"""dossiê estruturado de análise

Revision ID: 0007_analysis_dossie
Revises: 0006_case_structured_pieces
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_analysis_dossie"
down_revision = "0006_case_structured_pieces"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("analysis_dossie", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "analysis_dossie")
