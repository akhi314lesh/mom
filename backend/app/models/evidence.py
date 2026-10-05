"""
models/evidence.py — Evidence ORM model.

INVARIANT: Evidence records are immutable once stored (is_immutable=True).
Corrections create NEW Evidence records with source_type=HUMAN_CORRECTION.
The original Evidence is never mutated.

Every SemanticEvent, Decision, ActionItem, and Contradiction MUST have
at least one Evidence record in their evidence_ids JSON list.
An empty evidence_ids is a data integrity error.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Evidence(Base):
    """
    Immutable evidence record.

    source_type:
      TRANSCRIPT      - derived from a TranscriptSegment
      USER_MARK       - created by a UserMark (human input)
      MANUAL          - manually entered text
      IMPORT_DOC      - from an imported document
      HUMAN_CORRECTION - human correction of a prior claim

    Provenance chain: Evidence ← TranscriptSegment ← ProcessingRun{ASR}
    """
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    # Source references (at most one will be set)
    segment_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("transcript_segments.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_mark_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("user_marks.id", ondelete="SET NULL"),
        nullable=True,
    )
    processing_run_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True  # soft reference; ProcessingRun may be pruned
    )

    source_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_modality: Mapped[str] = mapped_column(String(20), nullable=False, default="AUDIO")
    timestamp_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_immutable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
