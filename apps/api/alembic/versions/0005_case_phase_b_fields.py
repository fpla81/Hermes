"""fase B: campos de pipeline + novos status do case

Revision ID: 0005_case_phase_b_fields
Revises: 0004_case_analysis_fields
Create Date: 2026-05-15
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0005_case_phase_b_fields"
down_revision = "0004_case_analysis_fields"
branch_labels = None
depends_on = None


NEW_STATUS_VALUES = ("preparing", "packaging", "rendering", "done")


def upgrade() -> None:
    for value in NEW_STATUS_VALUES:
        op.execute(f"ALTER TYPE case_status ADD VALUE IF NOT EXISTS '{value}'")

    op.add_column("cases", sa.Column("pieces_json", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("manifest", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("resource_validation", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("packet_index", sa.JSON(), nullable=True))
    op.add_column("cases", sa.Column("packets_key", sa.String(length=512), nullable=True))
    op.add_column("cases", sa.Column("minuta_md", sa.Text(), nullable=True))
    op.add_column("cases", sa.Column("docx_key", sa.String(length=512), nullable=True))


def downgrade() -> None:
    op.drop_column("cases", "docx_key")
    op.drop_column("cases", "minuta_md")
    op.drop_column("cases", "packets_key")
    op.drop_column("cases", "packet_index")
    op.drop_column("cases", "resource_validation")
    op.drop_column("cases", "manifest")
    op.drop_column("cases", "pieces_json")
    # Postgres não permite remover valores de ENUM sem recriar; mantemos os
    # valores novos no tipo. Casos pré-existentes seguem com status válidos.
