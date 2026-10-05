"""
api/meetings.py — Meeting CRUD and lifecycle endpoints.
"""
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.meeting import Meeting, MeetingLifecycle, ProcessingStatus, CaptureMode, PrivacyMode

router = APIRouter()


@router.get("/", summary="List all meetings")
async def list_meetings(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(Meeting).order_by(Meeting.date.desc()))
    meetings = result.scalars().all()
    return [_meeting_summary(m) for m in meetings]


@router.post("/", status_code=status.HTTP_201_CREATED, summary="Create a new meeting")
async def create_meeting(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    meeting = Meeting(
        id=str(uuid.uuid4()),
        title=body.get("title", "Untitled Meeting"),
        date=datetime.now(timezone.utc),
        capture_mode=body.get("capture_mode", CaptureMode.IMPORT),
        lifecycle_status=MeetingLifecycle.PREPARING,
        processing_status=ProcessingStatus.IDLE,
        privacy_mode=body.get("privacy_mode", PrivacyMode.LOCAL),
        quality_metrics={
            "transcript_quality": 0.0,
            "speaker_attribution_quality": 0.0,
            "decision_certainty": 0.0,
            "action_extraction_confidence": 0.0,
            "grounding_coverage": 0.0,
            "overall_confidence": 0.0,
            "weak_areas": [],
        },
    )
    db.add(meeting)
    await db.commit()
    await db.refresh(meeting)
    return _meeting_summary(meeting)


@router.get("/{meeting_id}", summary="Get meeting detail")
async def get_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    meeting = await _get_or_404(meeting_id, db)
    return _meeting_summary(meeting)


@router.patch("/{meeting_id}", summary="Update meeting fields")
async def update_meeting(meeting_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    meeting = await _get_or_404(meeting_id, db)
    for field in ("title", "description", "privacy_mode"):
        if field in body:
            setattr(meeting, field, body[field])
    await db.commit()
    await db.refresh(meeting)
    return _meeting_summary(meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meeting(meeting_id: str, db: AsyncSession = Depends(get_db)) -> None:
    meeting = await _get_or_404(meeting_id, db)
    await db.delete(meeting)
    await db.commit()


@router.get("/{meeting_id}/record", summary="Get canonical MeetingRecord")
async def get_meeting_record(meeting_id: str, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """
    Assemble and return the canonical MeetingRecord for this meeting.
    Phase 0: returns stub structure. Phase 1+: fully populated.
    """
    meeting = await _get_or_404(meeting_id, db)
    return {
        "meeting": _meeting_summary(meeting),
        "participants": [],
        "speakers": [],
        "transcript": [],
        "evidence": [],
        "events": [],
        "decisions": [],
        "action_items": [],
        "questions": [],
        "contradictions": [],
        "topics": [],
        "timeline": [],
        "review_items": [],
        "quality_metrics": meeting.quality_metrics or {},
        "artifacts": [],
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _get_or_404(meeting_id: str, db: AsyncSession) -> Meeting:
    result = await db.execute(select(Meeting).where(Meeting.id == meeting_id))
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail=f"Meeting {meeting_id} not found")
    return meeting


def _meeting_summary(m: Meeting) -> dict:
    return {
        "id": m.id,
        "title": m.title,
        "date": m.date.isoformat(),
        "capture_mode": m.capture_mode,
        "lifecycle_status": m.lifecycle_status,
        "processing_status": m.processing_status,
        "privacy_mode": m.privacy_mode,
        "quality_metrics": m.quality_metrics,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }
