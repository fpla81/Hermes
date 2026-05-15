import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Enum, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class CaseStatus(enum.StrEnum):
    draft = "draft"
    capturing = "capturing"
    captured = "captured"
    preparing = "preparing"
    analyzing = "analyzing"
    ready = "ready"
    packaging = "packaging"
    rendering = "rendering"
    done = "done"
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
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifact_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    analysis_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    anonymization_map: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pieces_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    manifest: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    resource_validation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    packet_index: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    packets_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    minuta_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    docx_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False, server_default=func.now(), onupdate=func.now()
    )

    @property
    def has_manifest(self) -> bool:
        return self.manifest is not None

    @property
    def has_packets(self) -> bool:
        return self.packets_key is not None

    @property
    def has_minuta(self) -> bool:
        return self.minuta_md is not None

    @property
    def has_docx(self) -> bool:
        return self.docx_key is not None
