"""
models/artifacts.py — Artifact ORM model.

ArtifactStatus tracks validity relative to current MeetingRecord.

INVARIANT: When a correction occurs, affected Artifact.status → STALE.
INVARIANT: Stale artifacts are cheaply regenerated from MeetingRecord.
INVARIANT: A STALE artifact does NOT trigger reprocessing of audio or ML stages.
"""
import uuid
from datetime import datetime
from enum import Enum
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ArtifactType(str, Enum):
    DOCX = "DOCX"
    PDF = "PDF"
    JSON = "JSON"
    CSV = "CSV"
    TRANSCRIPT_TXT = "TRANSCRIPT_TXT"
    EVIDENCE_JSON = "EVIDENCE_JSON"


class ArtifactStatus(str, Enum):
    CURRENT = "CURRENT"       # Reflects current MeetingRecord
    STALE = "STALE"           # MeetingRecord changed; needs regeneration
    GENERATING = "GENERATING" # Regeneration in progress
    FAILED = "FAILED"         # Last generation attempt failed


class Artifact(Base):
    __tablename__ = "artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=ArtifactStatus.GENERATING)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    stale_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stale_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    generation_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
