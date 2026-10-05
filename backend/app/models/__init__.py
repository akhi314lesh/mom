"""
models/__init__.py — Imports all ORM models so Alembic autogenerate
discovers them via the metadata.

Import order matters for foreign key resolution.
"""
from app.models.meeting import Meeting, MeetingSession  # noqa: F401
from app.models.capture import CaptureSession, CaptureSource  # noqa: F401
from app.models.participant import Participant, Speaker  # noqa: F401
from app.models.transcript import TranscriptSegment  # noqa: F401
from app.models.evidence import Evidence  # noqa: F401
from app.models.semantic import SemanticEvent, MeetingTopic  # noqa: F401
from app.models.decisions import Decision  # noqa: F401
from app.models.actions import ActionItem  # noqa: F401
from app.models.questions import Question  # noqa: F401
from app.models.contradictions import Contradiction  # noqa: F401
from app.models.knowledge import KnowledgeItem, TerminologyEntry  # noqa: F401
from app.models.review import ReviewItem  # noqa: F401
from app.models.processing import ProcessingRun, ProcessingLedger  # noqa: F401
from app.models.artifacts import Artifact  # noqa: F401
from app.models.brief import MeetingBrief  # noqa: F401
from app.models.marks import UserMark  # noqa: F401

__all__ = [
    "Meeting", "MeetingSession",
    "CaptureSession", "CaptureSource",
    "Participant", "Speaker",
    "TranscriptSegment",
    "Evidence",
    "SemanticEvent", "MeetingTopic",
    "Decision",
    "ActionItem",
    "Question",
    "Contradiction",
    "KnowledgeItem", "TerminologyEntry",
    "ReviewItem",
    "ProcessingRun", "ProcessingLedger",
    "Artifact",
    "MeetingBrief",
    "UserMark",
]
