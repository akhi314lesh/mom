"""
api/continuity.py — Cross-meeting ActionItem tracking and continuity endpoints.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.actions import ActionItem, ActionItemStatus
from app.pipeline.continuity import continuity_resolver
from app.pipeline.corrections import apply_human_correction

router = APIRouter()


@router.get("/actions", summary="List cross-meeting action items with lineage")
async def list_cross_meeting_actions(
    status: Optional[str] = None,
    owner_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all action items across meetings, enriched with originating meeting,
    last updated meeting, and owner information.
    """
    return await continuity_resolver.list_cross_meeting_actions(
        db=db,
        status=status if isinstance(status, str) else None,
        owner_id=owner_id if isinstance(owner_id, str) else None,
    )


@router.get("/actions/{action_id}/history", summary="Get cross-meeting lineage and evidence chain for an action item")
async def get_action_history(
    action_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the complete provenance and cross-meeting history for an ActionItem,
    including originating meeting, updates, and evidence items.
    """
    history = await continuity_resolver.get_action_continuity_history(db, action_id)
    if not history:
        raise HTTPException(status_code=404, detail="Action item not found")
    return history


@router.post("/meetings/{meeting_id}/resolve", summary="Trigger continuity resolution for a meeting")
async def resolve_meeting_continuity(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Scans prior pending action items and detects if this meeting advanced or resolved them.
    """
    updates = await continuity_resolver.resolve_meeting_continuity(db, meeting_id)
    return {
        "meeting_id": meeting_id,
        "updates_count": len(updates),
        "updates": updates,
    }


@router.patch("/actions/{action_id}/status", summary="Update action item status with cross-meeting provenance")
async def update_action_status_continuity(
    action_id: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Human update of action item status across meetings. Records immutable HUMAN evidence
    and updates last_updated_meeting_id.
    """
    new_status = body.get("status")
    meeting_id = body.get("meeting_id")
    if not new_status:
        raise HTTPException(status_code=400, detail="Missing status")

    res = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
    action = res.scalar_one_or_none()
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")

    old_status = action.status
    action.status = new_status
    action.review_state = "CONFIRMED"
    if meeting_id:
        action.last_updated_meeting_id = meeting_id

    await db.commit()

    # Track correction and provenance
    target_meeting = meeting_id or action.originating_meeting_id
    await apply_human_correction(
        db=db,
        meeting_id=target_meeting,
        target_type="ACTION_ITEM",
        target_id=action_id,
        field="status",
        old_value=old_status,
        new_value=new_status,
        origin_stage="CONTINUITY",
    )

    return {
        "id": action.id,
        "task": action.task,
        "status": action.status,
        "old_status": old_status,
        "last_updated_meeting_id": action.last_updated_meeting_id,
        "originating_meeting_id": action.originating_meeting_id,
    }
