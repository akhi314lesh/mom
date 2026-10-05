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
    Fulfills ADR-007: canonical aggregate view of meeting state.
    """
    from app.models.participant import Participant, Speaker
    from app.models.transcript import TranscriptSegment
    from app.models.decisions import Decision
    from app.models.actions import ActionItem
    from app.models.questions import Question
    from app.models.review import ReviewItem
    from app.models.artifacts import Artifact
    from app.models.evidence import Evidence

    meeting = await _get_or_404(meeting_id, db)

    parts_res = await db.execute(select(Participant).where(Participant.meeting_id == meeting_id))
    spks_res = await db.execute(select(Speaker).where(Speaker.meeting_id == meeting_id))
    segs_res = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.start_ms)
    )
    decs_res = await db.execute(select(Decision).where(Decision.meeting_id == meeting_id))
    acts_res = await db.execute(select(ActionItem).where(ActionItem.originating_meeting_id == meeting_id))
    ques_res = await db.execute(select(Question).where(Question.meeting_id == meeting_id))
    revs_res = await db.execute(select(ReviewItem).where(ReviewItem.meeting_id == meeting_id))
    arts_res = await db.execute(select(Artifact).where(Artifact.meeting_id == meeting_id))
    evs_res = await db.execute(select(Evidence).where(Evidence.meeting_id == meeting_id))

    participants = parts_res.scalars().all()
    part_name_map = {p.id: p.name for p in participants}

    speakers = spks_res.scalars().all()
    speaker_display_map = {
        s.id: part_name_map.get(s.resolved_participant_id, s.label)
        for s in speakers
    }

    transcript_list = [
        {
            "id": s.id,
            "speaker_id": s.speaker_id,
            "speaker_name": speaker_display_map.get(s.speaker_id, "Unknown"),
            "start_ms": s.start_ms,
            "end_ms": s.end_ms,
            "text": s.text,
            "asr_confidence": s.asr_confidence,
            "source_modality": s.source_modality,
        }
        for s in segs_res.scalars().all()
    ]

    decisions_list = [
        {
            "id": d.id,
            "text": d.text,
            "status": d.status,
            "confidence": d.confidence,
            "review_state": d.review_state,
            "evidence_ids": d.evidence_ids,
        }
        for d in decs_res.scalars().all()
    ]

    actions_list = [
        {
            "id": a.id,
            "task": a.task,
            "owner": part_name_map.get(a.owner_id, "Unassigned"),
            "owner_id": a.owner_id,
            "owner_confidence": a.owner_confidence,
            "deadline": a.deadline.isoformat() if a.deadline else None,
            "deadline_confidence": a.deadline_confidence,
            "status": a.status,
            "priority": a.priority,
            "confidence": a.confidence,
            "review_state": a.review_state,
            "evidence_ids": a.evidence_ids,
        }
        for a in acts_res.scalars().all()
    ]

    questions_list = [
        {
            "id": q.id,
            "text": q.text,
            "answered": q.answered,
            "answer_text": q.answer_text,
            "confidence": q.confidence,
            "evidence_ids": q.evidence_ids,
        }
        for q in ques_res.scalars().all()
    ]

    review_list = [
        {
            "id": r.id,
            "type": r.type,
            "question": r.question,
            "options": r.options,
            "context": r.context,
            "priority_score": r.priority_score,
            "status": r.status,
            "evidence_ids": r.evidence_ids,
        }
        for r in revs_res.scalars().all()
    ]

    artifacts_list = [
        {
            "id": a.id,
            "type": a.type,
            "status": a.status,
            "path": a.path,
            "file_size_bytes": a.file_size_bytes,
        }
        for a in arts_res.scalars().all()
    ]

    evidence_list = [
        {
            "id": e.id,
            "source_type": e.source_type,
            "timestamp_ms": e.timestamp_ms,
            "raw_text": e.raw_text,
            "confidence": e.confidence,
        }
        for e in evs_res.scalars().all()
    ]

    return {
        "meeting": _meeting_summary(meeting),
        "participants": [{"id": p.id, "name": p.name, "role": p.role} for p in participants],
        "speakers": [
            {
                "id": s.id,
                "label": s.label,
                "resolved_participant_id": s.resolved_participant_id,
                "resolution_confidence": s.resolution_confidence,
                "total_speaking_time_ms": s.total_speaking_time_ms,
            }
            for s in speakers
        ],
        "transcript": transcript_list,
        "evidence": evidence_list,
        "decisions": decisions_list,
        "action_items": actions_list,
        "questions": questions_list,
        "review_items": review_list,
        "quality_metrics": meeting.quality_metrics or {},
        "artifacts": artifacts_list,
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
