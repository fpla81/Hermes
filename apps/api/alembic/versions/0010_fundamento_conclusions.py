"""fundamentos: separa corpo (literal) das duas conclusões pré-prontas

Revision ID: 0010_fundamento_conclusions
Revises: 0009_fundamentos
Create Date: 2026-05-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_fundamento_conclusions"
down_revision = "0009_fundamentos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fundamentos",
        sa.Column("conclusao_provimento", sa.Text(), nullable=True),
    )
    op.add_column(
        "fundamentos",
        sa.Column("conclusao_nao_conhecimento", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("fundamentos", "conclusao_nao_conhecimento")
    op.drop_column("fundamentos", "conclusao_provimento")
