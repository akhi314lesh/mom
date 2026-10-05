"""api/actions.py — ActionItem CRUD."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.actions import ActionItem

router = APIRouter()

@router.get("/", summary="List all action items (cross-meeting)")
async def list_all_actions(status: str | None = None, db: AsyncSession = Depends(get_db)) -> list[dict]:
    q = select(ActionItem)
    if status:
        q = q.where(ActionItem.status == status)
    result = await db.execute(q.order_by(ActionItem.originating_meeting_id))
    items = result.scalars().all()
    return [_action_dict(a) for a in items]

@router.get("/meeting/{meeting_id}", summary="List action items for a meeting")
async def list_meeting_actions(meeting_id: str, db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(ActionItem).where(ActionItem.originating_meeting_id == meeting_id))
    return [_action_dict(a) for a in result.scalars().all()]

@router.patch("/{action_id}", summary="Update an action item")
async def update_action(action_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return {"error": "Action item not found"}
    for field in ("status", "priority", "task", "deadline"):
        if field in body:
            setattr(action, field, body[field])
    await db.commit()
    return _action_dict(action)

def _action_dict(a: ActionItem) -> dict:
    return {
        "id": a.id, "task": a.task, "owner_id": a.owner_id,
        "owner_confidence": a.owner_confidence, "deadline": str(a.deadline) if a.deadline else None,
        "deadline_confidence": a.deadline_confidence, "status": a.status, "priority": a.priority,
        "confidence": a.confidence, "review_state": a.review_state,
        "originating_meeting_id": a.originating_meeting_id,
        "last_updated_meeting_id": a.last_updated_meeting_id,
        "evidence_ids": a.evidence_ids,
    }
