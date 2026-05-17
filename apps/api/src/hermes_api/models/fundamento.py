import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class Fundamento(Base):
    __tablename__ = "fundamentos"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    tema: Mapped[str] = mapped_column(String(255), nullable=False)
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    corpo_md: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)
    resumo: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusao_provimento: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusao_nao_conhecimento: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_case_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("cases.id", ondelete="SET NULL"),
        nullable=True,
    )
    usage_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
