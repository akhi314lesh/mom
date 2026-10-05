"""
api/people.py — Participant directory and cross-meeting history (Phase 6).
"""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.participant import Participant, Speaker
from app.models.meeting import Meeting
from app.models.actions import ActionItem, ActionItemStatus

router = APIRouter()


@router.get("/directory", summary="Full participant directory with cross-meeting metrics")
async def get_participant_directory(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all participants with aggregated cross-meeting statistics:
    meetings attended, speaking time, assigned open/completed action items, and resolved aliases.
    """
    # 1. Fetch all participants
    p_res = await db.execute(select(Participant).order_by(Participant.name))
    participants = p_res.scalars().all()

    # Deduplicate by name across meetings
    unique_people: Dict[str, Dict[str, Any]] = {}

    for p in participants:
        name_key = p.name.strip().lower()
        if name_key not in unique_people:
            unique_people[name_key] = {
                "id": p.id,
                "name": p.name,
                "role": p.role,
                "email": p.email,
                "aliases": list(p.aliases or []),
                "meeting_ids": set([p.meeting_id] if p.meeting_id else []),
                "total_speaking_time_ms": 0,
                "open_actions_count": 0,
                "completed_actions_count": 0,
                "resolved_speaker_labels": set(),
            }
        else:
            if p.meeting_id:
                unique_people[name_key]["meeting_ids"].add(p.meeting_id)
            if p.role and unique_people[name_key]["role"] in ("Team Member", "Participant", ""):
                unique_people[name_key]["role"] = p.role

    # 2. Fetch speakers to calculate speaking time & speaker labels
    spk_res = await db.execute(select(Speaker))
    speakers = spk_res.scalars().all()
    part_id_to_name_key = {p.id: p.name.strip().lower() for p in participants}

    for spk in speakers:
        if spk.resolved_participant_id and spk.resolved_participant_id in part_id_to_name_key:
            name_key = part_id_to_name_key[spk.resolved_participant_id]
            if name_key in unique_people:
                unique_people[name_key]["total_speaking_time_ms"] += (spk.total_speaking_time_ms or 0)
                unique_people[name_key]["resolved_speaker_labels"].add(spk.label)
                if spk.meeting_id:
                    unique_people[name_key]["meeting_ids"].add(spk.meeting_id)

    # 3. Fetch action items to calculate open and completed counts
    act_res = await db.execute(select(ActionItem))
    actions = act_res.scalars().all()

    for act in actions:
        if act.owner_id and act.owner_id in part_id_to_name_key:
            name_key = part_id_to_name_key[act.owner_id]
            if name_key in unique_people:
                if act.status in (ActionItemStatus.PENDING, ActionItemStatus.IN_PROGRESS, ActionItemStatus.BLOCKED):
                    unique_people[name_key]["open_actions_count"] += 1
                elif act.status == ActionItemStatus.COMPLETED:
                    unique_people[name_key]["completed_actions_count"] += 1

    result: List[Dict[str, Any]] = []
    for p_data in unique_people.values():
        result.append({
            "id": p_data["id"],
            "name": p_data["name"],
            "role": p_data["role"],
            "email": p_data["email"],
            "aliases": p_data["aliases"],
            "meetings_count": len(p_data["meeting_ids"]),
            "total_speaking_time_ms": p_data["total_speaking_time_ms"],
            "total_speaking_time_min": round(p_data["total_speaking_time_ms"] / 60000, 1),
            "open_actions_count": p_data["open_actions_count"],
            "completed_actions_count": p_data["completed_actions_count"],
            "resolved_speaker_labels": list(p_data["resolved_speaker_labels"]),
        })

    return result


@router.get("/{participant_id}/history", summary="Detailed cross-meeting history for a participant")
async def get_participant_history(
    participant_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns full meeting attendance and action items history for a participant.
    """
    p_res = await db.execute(select(Participant).where(Participant.id == participant_id))
    participant = p_res.scalar_one_or_none()
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Find all participant instances with same name
    same_name_res = await db.execute(
        select(Participant).where(Participant.name.ilike(participant.name))
    )
    same_participants = same_name_res.scalars().all()
    part_ids = [p.id for p in same_participants]
    meeting_ids = [p.meeting_id for p in same_participants if p.meeting_id]

    # Fetch meetings
    meetings: List[Dict[str, Any]] = []
    if meeting_ids:
        m_res = await db.execute(select(Meeting).where(Meeting.id.in_(meeting_ids)).order_by(Meeting.date.desc()))
        for m in m_res.scalars().all():
            meetings.append({
                "id": m.id,
                "title": m.title,
                "date": str(m.date),
                "lifecycle_status": m.lifecycle_status,
            })

    # Fetch actions assigned
    act_res = await db.execute(
        select(ActionItem).where(ActionItem.owner_id.in_(part_ids)).order_by(ActionItem.status)
    )
    actions = [
        {
            "id": a.id,
            "task": a.task,
            "status": a.status,
            "priority": a.priority,
            "deadline": str(a.deadline) if a.deadline else None,
            "originating_meeting_id": a.originating_meeting_id,
            "last_updated_meeting_id": a.last_updated_meeting_id,
        }
        for a in act_res.scalars().all()
    ]

    return {
        "id": participant.id,
        "name": participant.name,
        "role": participant.role,
        "meetings_attended": meetings,
        "actions_assigned": actions,
    }
