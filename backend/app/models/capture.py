"""
models/capture.py — CaptureSession and CaptureSource ORM models.

CaptureSession holds the EvidenceManifest (what evidence is available/unavailable)
and AudioSourceStatus (live source state) as JSON value objects.

The agent MUST read evidence_manifest.unavailable_sources before any pipeline stage.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class AudioSourceState(str, Enum):
    MICROPHONE_ONLY = "MICROPHONE_ONLY"
    SYSTEM_ONLY = "SYSTEM_ONLY"
    MICROPHONE_AND_SYS = "MICROPHONE_AND_SYS"
    NO_AUDIO = "NO_AUDIO"


class CaptureSourceType(str, Enum):
    MICROPHONE = "MICROPHONE"
    SYSTEM_AUDIO = "SYSTEM_AUDIO"
    IMPORT_FILE = "IMPORT_FILE"
    MANUAL = "MANUAL"


class CaptureSourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    UNAVAILABLE = "UNAVAILABLE"


class CaptureSession(Base):
    """
    Tracks a capture session for a meeting.

    evidence_manifest: JSON value object declaring available/unavailable sources.
        Schema: {
            "available_sources": ["AUDIO", "TIMESTAMPS"],
            "unavailable_sources": ["VIDEO", "SYSTEM_AUDIO"],
            "degradation_reason": "System audio WASAPI unavailable"
        }

    audio_source_status: JSON value object for live source state.
        Schema: {
            "state": "MICROPHONE_ONLY",
            "microphone_available": true,
            "microphone_device": "Default Microphone",
            "system_audio_available": false,
            "system_audio_device": null,
            "degradation_reason": "WASAPI loopback not supported",
            "fallback_applied": true
        }
    """
    __tablename__ = "capture_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    capture_mode: Mapped[str] = mapped_column(String(20), nullable=False)
    audio_source_state: Mapped[str] = mapped_column(
        String(30), nullable=False, default=AudioSourceState.NO_AUDIO
    )

    # JSON value objects (embedded, not separate tables)
    audio_source_status: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    evidence_manifest: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {
            "available_sources": [],
            "unavailable_sources": [],
            "degradation_reason": None,
        },
    )

    privacy_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="LOCAL")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    meeting: Mapped["Meeting"] = relationship(back_populates="capture_sessions")
    sources: Mapped[list["CaptureSource"]] = relationship(
        back_populates="capture_session", cascade="all, delete-orphan"
    )


class CaptureSource(Base):
    """
    Individual audio/input source within a capture session.
    Each source tracks its own status independently.
    A source failure does NOT kill the CaptureSession.
    """
    __tablename__ = "capture_sources"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    capture_session_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("capture_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=CaptureSourceStatus.UNAVAILABLE
    )
    device_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    file_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    degradation_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    capture_session: Mapped["CaptureSession"] = relationship(back_populates="sources")
