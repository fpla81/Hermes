"""Tabela de Recursos de Revista Repetitivos do TST (cache local)

Revision ID: 0011_tema_repetitivo
Revises: 0010_fundamento_conclusions
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_tema_repetitivo"
down_revision = "0010_fundamento_conclusions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "temas_repetitivos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False, unique=True, index=True),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("situacao", sa.String(32), nullable=False, index=True),
        sa.Column("tese", sa.Text(), nullable=True),
        sa.Column("link", sa.Text(), nullable=True),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("temas_repetitivos")
