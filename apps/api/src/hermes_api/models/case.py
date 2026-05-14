import enum
import uuid
from datetime import datetime

from sqlalchemy import Enum, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class CaseStatus(enum.StrEnum):
    draft = "draft"
    capturing = "capturing"
    captured = "captured"
    analyzing = "analyzing"
    ready = "ready"
    error = "error"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    numero_processo: Mapped[str] = mapped_column(String(64), nullable=False)
    titulo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[CaseStatus] = mapped_column(
        Enum(CaseStatus, name="case_status"),
        nullable=False,
        default=CaseStatus.draft,
    )
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )
