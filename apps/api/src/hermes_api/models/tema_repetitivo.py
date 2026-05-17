import uuid
from datetime import datetime

from sqlalchemy import Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class TemaRepetitivo(Base):
    __tablename__ = "temas_repetitivos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, unique=True, index=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    situacao: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    tese: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
