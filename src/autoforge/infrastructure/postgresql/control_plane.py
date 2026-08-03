from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class ControlPlaneBase(DeclarativeBase):
    pass


class GenerationJobRecord(ControlPlaneBase):
    __tablename__ = "autoforge_generation_jobs"

    job_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    idempotency_key: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(32), index=True)
    document: Mapped[dict[str, Any]] = mapped_column(JSONB)
    revision: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class AuditRecordRow(ControlPlaneBase):
    __tablename__ = "autoforge_audit_records"

    event_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    event_type: Mapped[str] = mapped_column(String(255), index=True)
    event_version: Mapped[str] = mapped_column(String(32))
    event_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str | None] = mapped_column(String(128), index=True)
    causation_id: Mapped[str | None] = mapped_column(String(128))
    job_id: Mapped[str | None] = mapped_column(String(128), index=True)
    producer: Mapped[str | None] = mapped_column(String(255))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload_redaction: Mapped[str] = mapped_column(
        Text, server_default="envelope_only"
    )
