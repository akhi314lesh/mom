"""
models/marks.py — UserMark ORM model.

UserMark represents a Ctrl+Shift+M "Mark Moment" event.
These are HUMAN-sourced events (source is always "HUMAN").
processing_priority influences pipeline scheduling: marked regions
are processed first and with higher-tier reasoning.

INVARIANT: source is always "HUMAN". Never override this field.
"""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class UserMark(Base):
    __tablename__ = "user_marks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False)
    capture_session_id: Mapped[str] = mapped_column(String(36), ForeignKey("capture_sessions.id", ondelete="CASCADE"), nullable=False)
    timestamp_ms: Mapped[int] = mapped_column(Integer, nullable=False)  # meeting-relative
    wall_clock_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False, default="USER_MARK")
    optional_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str] = mapped_column(String(10), nullable=False, default="HUMAN")  # always HUMAN
    processing_priority: Mapped[float] = mapped_column(Float, nullable=False, default=0.9)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
