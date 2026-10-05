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
    from app.models.marks import UserMark
    from app.models.contradictions import Contradiction
    from app.models.semantic import SemanticEvent

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
    marks_res = await db.execute(
        select(UserMark).where(UserMark.meeting_id == meeting_id).order_by(UserMark.timestamp_ms)
    )
    cons_res = await db.execute(select(Contradiction).where(Contradiction.meeting_id == meeting_id))
    sems_res = await db.execute(
        select(SemanticEvent)
        .where(SemanticEvent.meeting_id == meeting_id)
        .order_by(SemanticEvent.start_ms)
    )

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

    user_marks_list = [
        {
            "id": m.id,
            "meeting_id": m.meeting_id,
            "capture_session_id": m.capture_session_id,
            "timestamp_ms": m.timestamp_ms,
            "wall_clock_time": m.wall_clock_time.isoformat() if m.wall_clock_time else None,
            "event_type": m.event_type,
            "optional_text": m.optional_text,
            "source": m.source,
            "processing_priority": m.processing_priority,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in marks_res.scalars().all()
    ]

    contradictions_list = [
        {
            "id": c.id,
            "meeting_id": c.meeting_id,
            "contradiction_type": c.contradiction_type,
            "description": c.description,
            "event_a_id": c.event_a_id,
            "event_b_id": c.event_b_id,
            "is_cross_meeting": c.is_cross_meeting,
            "review_state": c.review_state,
            "confidence": c.confidence,
        }
        for c in cons_res.scalars().all()
    ]

    semantic_events_list = [
        {
            "id": se.id,
            "meeting_id": se.meeting_id,
            "event_type": se.event_type,
            "text": se.text,
            "start_ms": se.start_ms,
            "end_ms": se.end_ms,
            "confidence": se.confidence,
            "review_state": se.review_state,
            "evidence_ids": se.evidence_ids,
        }
        for se in sems_res.scalars().all()
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
        "user_marks": user_marks_list,
        "contradictions": contradictions_list,
        "semantic_events": semantic_events_list,
        "decisions": decisions_list,
        "action_items": actions_list,
        "questions": questions_list,
        "review_items": review_list,
        "quality_metrics": meeting.quality_metrics or {},
        "artifacts": artifacts_list,
    }


@router.get("/participants/all", summary="List all participants across meetings")
async def list_all_participants(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """Returns all unique participants across the organizational memory."""
    from app.models.participant import Participant

    result = await db.execute(select(Participant).order_by(Participant.name))
    participants = result.scalars().all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "email": p.email,
            "role": p.role,
            "meeting_id": p.meeting_id,
        }
        for p in participants
    ]


@router.post("/{meeting_id}/speaker/{speaker_id}/resolve", summary="Resolve speaker to a participant (Phase 3)")
async def resolve_speaker(
    meeting_id: str,
    speaker_id: str,
    body: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Resolves a speaker label to a participant with HUMAN verification.
    Applies human correction, creates immutable Evidence, invalidates downstream
    stages (SEMANTIC/VALIDATION/ARTIFACTS) while preserving ASR and diarization (ADR-010).
    """
    from app.models.participant import Participant, Speaker
    from app.models.review import ReviewItem
    from app.pipeline.corrections import apply_human_correction

    await _get_or_404(meeting_id, db)

    spk_res = await db.execute(
        select(Speaker).where(Speaker.id == speaker_id, Speaker.meeting_id == meeting_id)
    )
    spk = spk_res.scalar_one_or_none()
    if not spk:
        raise HTTPException(404, "Speaker not found")

    old_resolved_id = spk.resolved_participant_id
    participant_name = body.get("name", "").strip()
    participant_role = body.get("role", "").strip()

    # Find or create Participant
    part = None
    if body.get("participant_id"):
        part_res = await db.execute(select(Participant).where(Participant.id == body["participant_id"]))
        part = part_res.scalar_one_or_none()

    if not part and participant_name:
        part_res = await db.execute(
            select(Participant).where(Participant.meeting_id == meeting_id, Participant.name == participant_name)
        )
        part = part_res.scalar_one_or_none()
        if not part:
            part = Participant(
                id=str(uuid.uuid4()),
                meeting_id=meeting_id,
                name=participant_name,
                role=participant_role or "Team Member",
            )
            db.add(part)
            await db.flush()

    if not part:
        raise HTTPException(400, "Must provide valid participant_id or name")

    spk.resolved_participant_id = part.id
    spk.resolution_confidence = 1.0
    spk.resolution_source = "HUMAN"

    # Resolve any pending review items for this speaker
    rev_res = await db.execute(
        select(ReviewItem).where(
            ReviewItem.meeting_id == meeting_id,
            ReviewItem.type == "SPEAKER_IDENTITY",
            ReviewItem.status == "PENDING",
        )
    )
    for rev in rev_res.scalars().all():
        rev.status = "RESOLVED"
        rev.resolution = part.name

    await db.commit()

    # Apply human correction and artifact regeneration (ADR-008, ADR-011)
    corr_res = await apply_human_correction(
        db=db,
        meeting_id=meeting_id,
        target_type="SPEAKER",
        target_id=speaker_id,
        field="resolved_participant",
        old_value=old_resolved_id or spk.label,
        new_value=part.name,
        origin_stage="IDENTITY",
    )

    return {
        "speaker_id": speaker_id,
        "resolved_to": part.name,
        "participant_id": part.id,
        "resolution_source": "HUMAN",
        "confidence": 1.0,
        "correction": corr_res,
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
        "briefing_id": m.briefing_id,
        "description": m.description,
        "quality_metrics": m.quality_metrics,
        "created_at": m.created_at.isoformat() if m.created_at else None,
        "updated_at": m.updated_at.isoformat() if m.updated_at else None,
    }
