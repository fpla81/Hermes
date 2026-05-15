"""structured pieces e blueprint do despacho

Revision ID: 0006_case_structured_pieces
Revises: 0005_case_phase_b_fields
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0006_case_structured_pieces"
down_revision = "0005_case_phase_b_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cases", sa.Column("structured_pieces", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("despacho_blueprint", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "despacho_blueprint")
    op.drop_column("cases", "structured_pieces")
