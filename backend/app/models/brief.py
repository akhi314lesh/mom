"""models/brief.py — MeetingBrief ORM model (pre-meeting context)."""
import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MeetingBrief(Base):
    __tablename__ = "meeting_briefs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    meeting_id: Mapped[str] = mapped_column(String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    previous_meeting_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    open_action_item_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_topics: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    relevant_documents: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    unresolved_question_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
