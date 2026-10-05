"""
models/participant.py — Participant and Speaker ORM models.

Participant: a named person in a meeting (human-supplied or extracted).
Speaker: a diarization label (e.g. "SPEAKER_1") that is resolved to a Participant.

Speaker.resolution_confidence is a field-level confidence score.
Speaker.resolution_source must be HUMAN | SYSTEM | INFERRED.
"""
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    pass


class Participant(Base):
    """
    A named person in a meeting.
    aliases: JSON list of name variants (e.g. ["Akhil", "Akhilesh", "AK"])
    is_self: True if this is the user running the system.
    """
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    email: Mapped[str | None] = mapped_column(String(500), nullable=True)
    aliases: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    role: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_self: Mapped[bool] = mapped_column(default=False)

    speakers: Mapped[list["Speaker"]] = relationship(
        back_populates="resolved_participant",
        foreign_keys="Speaker.resolved_participant_id",
    )


class Speaker(Base):
    """
    A diarization-assigned speaker label, optionally resolved to a Participant.

    resolution_source values:
      HUMAN:    User confirmed the mapping
      SYSTEM:   System auto-resolved with high confidence
      INFERRED: Low-confidence guess; requires review

    INVARIANT: resolution_source=INFERRED is NEVER sufficient to set verified=True
               on downstream KnowledgeItems referencing this speaker.
    """
    __tablename__ = "speakers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "SPEAKER_1"
    resolved_participant_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolution_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    resolution_source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="INFERRED"
    )
    total_speaking_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    resolved_participant: Mapped["Participant | None"] = relationship(
        back_populates="speakers",
        foreign_keys=[resolved_participant_id],
    )
