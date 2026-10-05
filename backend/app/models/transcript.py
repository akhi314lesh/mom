"""
models/transcript.py — TranscriptSegment ORM model.

Each segment represents one utterance with ASR confidence (field-level).
Segments are immutable once created. Edits set is_edited=True and
create a new Evidence record with source_type=HUMAN_CORRECTION.
"""
import uuid

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TranscriptSegment(Base):
    """
    A single timed utterance from the transcript.

    asr_confidence: field-level confidence from the ASR adapter.
    is_edited: set True when a human edits the text.
    source_modality: AUDIO | MANUAL | IMPORT
    """
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    speaker_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("speakers.id", ondelete="SET NULL"), nullable=True
    )
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(10), nullable=False, default="en")
    asr_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_edited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    edited_by: Mapped[str | None] = mapped_column(String(20), nullable=True)  # HUMAN | SYSTEM
    source_modality: Mapped[str] = mapped_column(
        String(20), nullable=False, default="AUDIO"
    )  # AUDIO | MANUAL | IMPORT
