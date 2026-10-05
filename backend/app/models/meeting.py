"""
models/meeting.py — Meeting and MeetingSession ORM models.

Meeting is the root aggregate. MeetingSession tracks individual
recording/import/review sessions within a meeting.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.capture import CaptureSession
    from app.models.brief import MeetingBrief


class CaptureMode(str, Enum):
    RECORDING = "RECORDING"
    OVERLAY = "OVERLAY"
    IMPORT = "IMPORT"
    NOTES_ONLY = "NOTES_ONLY"


class MeetingLifecycle(str, Enum):
    PREPARING = "PREPARING"
    CAPTURING = "CAPTURING"
    PROCESSING = "PROCESSING"
    REVIEWING = "REVIEWING"
    FINALIZED = "FINALIZED"
    FOLLOW_UP = "FOLLOW_UP"


class ProcessingStatus(str, Enum):
    IDLE = "IDLE"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class PrivacyMode(str, Enum):
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    HYBRID = "HYBRID"


class Meeting(Base):
    """
    Root entity for a meeting.

    quality_metrics is a JSON value object containing field-level quality scores.
    It is NOT a separate table — see DATA_AND_PROVENANCE_MODEL.md.
    """
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capture_mode: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CaptureMode.IMPORT
    )
    lifecycle_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MeetingLifecycle.PREPARING
    )
    processing_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ProcessingStatus.IDLE
    )
    privacy_mode: Mapped[str] = mapped_column(
        String(10), nullable=False, default=PrivacyMode.LOCAL
    )
    briefing_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # Embedded value object: MeetingQualityMetrics
    quality_metrics: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    sessions: Mapped[list["MeetingSession"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )
    capture_sessions: Mapped[list["CaptureSession"]] = relationship(
        back_populates="meeting", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Meeting id={self.id} title={self.title!r} status={self.lifecycle_status}>"


class MeetingSession(Base):
    """
    Tracks individual recording/import/review sessions within a meeting.
    A meeting may have multiple sessions (e.g., two recording segments).
    """
    __tablename__ = "meeting_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    session_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="IMPORT"
    )  # LIVE | IMPORT | REVIEW

    meeting: Mapped["Meeting"] = relationship(back_populates="sessions")
