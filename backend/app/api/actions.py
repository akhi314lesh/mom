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

@router.patch("/{action_id}", summary="Update an action item with human correction tracking")
async def update_action(action_id: str, body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    from app.pipeline.corrections import apply_human_correction

    result = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
    action = result.scalar_one_or_none()
    if not action:
        return {"error": "Action item not found"}

    corrections_applied = []
    for field in ("status", "priority", "task", "deadline", "owner_id"):
        if field in body and getattr(action, field) != body[field]:
            old_val = getattr(action, field)
            new_val = body[field]
            setattr(action, field, new_val)
            action.review_state = "CONFIRMED"
            corrections_applied.append((field, old_val, new_val))

    await db.commit()

    # Apply provenance and invalidation for each correction
    for field, old_val, new_val in corrections_applied:
        await apply_human_correction(
            db=db,
            meeting_id=action.originating_meeting_id,
            target_type="ACTION_ITEM",
            target_id=action_id,
            field=field,
            old_value=old_val,
            new_value=new_val,
            origin_stage="SEMANTIC",
        )

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
