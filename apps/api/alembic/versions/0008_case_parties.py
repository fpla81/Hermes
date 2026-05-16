"""partes do processo para anonimização determinística

Revision ID: 0008_case_parties
Revises: 0007_analysis_dossie
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_case_parties"
down_revision = "0007_analysis_dossie"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("parties", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "parties")
