"""backend/app/api/integrations.py — External Integrations & Meeting Briefs API."""
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.meeting import Meeting, MeetingLifecycle, ProcessingStatus, CaptureMode, PrivacyMode
from app.models.brief import MeetingBrief
from app.models.participant import Participant
from app.models.actions import ActionItem
from app.models.questions import Question
from app.models.evidence import Evidence
from app.integrations.manager import integration_manager
from app.integrations.calendar.base import CalendarEvent
from app.integrations.calendar.brief_generator import brief_generator
from app.integrations.tasks.base import TaskExportRequest, TaskExportReceipt

router = APIRouter()


class ImportMeetingRequest(BaseModel):
    event_id: str
    auto_generate_brief: bool = True


@router.get("/settings", summary="Get integration settings")
async def get_settings() -> Dict[str, Any]:
    return integration_manager.get_settings()


@router.post("/settings", summary="Update integration settings")
async def update_settings(body: Dict[str, Any]) -> Dict[str, Any]:
    return integration_manager.update_settings(body)


@router.post("/test/{provider}", summary="Test integration provider connectivity")
async def test_provider(provider: str) -> Dict[str, Any]:
    try:
        return await integration_manager.test_connection(provider)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/calendar/events", summary="List upcoming calendar events")
async def list_calendar_events() -> List[CalendarEvent]:
    return await integration_manager.get_upcoming_events()


@router.post("/calendar/import-meeting", status_code=status.HTTP_201_CREATED, summary="Import calendar event as a meeting")
async def import_calendar_meeting(
    payload: ImportMeetingRequest,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    events = await integration_manager.get_upcoming_events()
    matched_event: Optional[CalendarEvent] = None
    for ev in events:
        if ev.id == payload.event_id:
            matched_event = ev
            break

    if not matched_event:
        raise HTTPException(status_code=404, detail=f"Calendar event {payload.event_id} not found")

    # 1. Create meeting
    meeting_id = str(uuid.uuid4())
    meeting = Meeting(
        id=meeting_id,
        title=matched_event.title,
        date=matched_event.start_time,
        capture_mode=CaptureMode.IMPORT,
        lifecycle_status=MeetingLifecycle.PREPARING,
        processing_status=ProcessingStatus.IDLE,
        privacy_mode=PrivacyMode.LOCAL,
        description=matched_event.description or f"Imported from {matched_event.provider.capitalize()} Calendar",
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

    # 2. Add attendees as participants
    for att in matched_event.attendees:
        p = Participant(
            id=str(uuid.uuid4()),
            meeting_id=meeting_id,
            name=att.name,
            email=att.email,
            aliases=[att.name.lower(), att.name.split()[0].lower()],
            role="ATTENDEE",
            is_self=(att.name.lower() == "akhilesh"),
        )
        db.add(p)

    await db.commit()
    await db.refresh(meeting)

    # 3. Generate Brief if requested
    brief_data = None
    if payload.auto_generate_brief:
        brief = await brief_generator.generate_brief_for_meeting(db, meeting_id, matched_event)
        brief_data = {
            "id": brief.id,
            "title": brief.title,
            "expected_topics": brief.expected_topics,
            "relevant_documents": brief.relevant_documents,
            "previous_meeting_ids": brief.previous_meeting_ids,
            "open_action_item_ids": brief.open_action_item_ids,
            "unresolved_question_ids": brief.unresolved_question_ids,
            "generated_at": brief.generated_at.isoformat() if brief.generated_at else None,
        }

    return {
        "status": "imported",
        "meeting": {
            "id": meeting.id,
            "title": meeting.title,
            "date": meeting.date.isoformat(),
            "capture_mode": meeting.capture_mode.value if hasattr(meeting.capture_mode, "value") else str(meeting.capture_mode),
            "lifecycle_status": meeting.lifecycle_status.value if hasattr(meeting.lifecycle_status, "value") else str(meeting.lifecycle_status),
            "briefing_id": meeting.briefing_id,
        },
        "brief": brief_data,
    }


@router.post("/tasks/export", summary="Export action item to external tracker")
async def export_task(
    payload: TaskExportRequest,
    db: AsyncSession = Depends(get_db)
) -> TaskExportReceipt:
    # 1. Fetch Action Item
    stmt = select(ActionItem).where(ActionItem.id == payload.action_item_id)
    res = await db.execute(stmt)
    action = res.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail=f"ActionItem {payload.action_item_id} not found")

    # 2. Fetch Originating Meeting
    m_stmt = select(Meeting).where(Meeting.id == action.originating_meeting_id)
    m_res = await db.execute(m_stmt)
    meeting = m_res.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Originating meeting not found")

    # 3. Fetch evidence quote
    evidence_quote = None
    if action.evidence_ids:
        ev_stmt = select(Evidence).where(Evidence.id == action.evidence_ids[0])
        ev_res = await db.execute(ev_stmt)
        ev = ev_res.scalar_one_or_none()
        if ev:
            evidence_quote = ev.raw_text

    # 4. Fetch Owner Name
    owner_name = payload.assignee_override
    if not owner_name and action.owner_id:
        p_stmt = select(Participant).where(Participant.id == action.owner_id)
        p_res = await db.execute(p_stmt)
        p = p_res.scalar_one_or_none()
        if p:
            owner_name = p.name

    options = {
        "project_or_repo": payload.project_or_repo,
        "labels": payload.labels,
    }

    try:
        receipt = await integration_manager.export_action_item(
            action=action,
            meeting=meeting,
            destination=payload.destination,
            evidence_quote=evidence_quote,
            owner_name=owner_name,
            options=options,
        )
        return receipt
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/meetings/{meeting_id}/brief", summary="Get meeting brief and enriched context")
async def get_meeting_brief(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    b_stmt = select(MeetingBrief).where(MeetingBrief.meeting_id == meeting_id)
    b_res = await db.execute(b_stmt)
    brief = b_res.scalar_one_or_none()

    if not brief:
        # Check if meeting exists
        m_stmt = select(Meeting).where(Meeting.id == meeting_id)
        m_res = await db.execute(m_stmt)
        meeting = m_res.scalar_one_or_none()
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")

        # Auto generate if not present
        brief = await brief_generator.generate_brief_for_meeting(db, meeting_id)

    # Enrich previous meetings
    prev_meetings = []
    if brief.previous_meeting_ids:
        pm_stmt = select(Meeting).where(Meeting.id.in_(brief.previous_meeting_ids))
        pm_res = await db.execute(pm_stmt)
        for m in pm_res.scalars().all():
            prev_meetings.append({"id": m.id, "title": m.title, "date": m.date.isoformat()})

    # Enrich open action items
    open_actions = []
    if brief.open_action_item_ids:
        act_stmt = select(ActionItem).where(ActionItem.id.in_(brief.open_action_item_ids))
        act_res = await db.execute(act_stmt)
        for a in act_res.scalars().all():
            open_actions.append({
                "id": a.id,
                "task": a.task,
                "status": a.status.value if hasattr(a.status, "value") else str(a.status),
                "priority": a.priority.value if hasattr(a.priority, "value") else (str(a.priority) if a.priority else "MEDIUM"),
                "deadline": a.deadline.isoformat() if a.deadline else None,
            })

    # Enrich unresolved questions
    unresolved_questions = []
    if brief.unresolved_question_ids:
        q_stmt = select(Question).where(Question.id.in_(brief.unresolved_question_ids))
        q_res = await db.execute(q_stmt)
        for q in q_res.scalars().all():
            unresolved_questions.append({"id": q.id, "text": q.text})

    return {
        "id": brief.id,
        "meeting_id": brief.meeting_id,
        "title": brief.title,
        "expected_topics": brief.expected_topics,
        "relevant_documents": brief.relevant_documents,
        "previous_meetings": prev_meetings,
        "open_action_items": open_actions,
        "unresolved_questions": unresolved_questions,
        "generated_at": brief.generated_at.isoformat() if brief.generated_at else None,
    }


@router.post("/meetings/{meeting_id}/generate-brief", summary="Regenerate pre-meeting brief")
async def regenerate_meeting_brief(
    meeting_id: str,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    brief = await brief_generator.generate_brief_for_meeting(db, meeting_id)
    return await get_meeting_brief(meeting_id, db)
