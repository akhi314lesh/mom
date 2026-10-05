"""api/capture.py — Capture session management."""
from fastapi import APIRouter
router = APIRouter()

@router.get("/{meeting_id}/session", summary="Get active capture session")
async def get_capture_session(meeting_id: str) -> dict:
    return {"meeting_id": meeting_id, "capture_session": None, "message": "Phase 4: overlay implementation pending"}

@router.post("/{meeting_id}/mark", summary="Create a UserMark (Mark Moment)")
async def create_user_mark(meeting_id: str, body: dict) -> dict:
    """Phase 4: Creates a UserMark event. Stub returns confirmation."""
    return {"meeting_id": meeting_id, "mark_created": False, "message": "Phase 4: Mark Moment pending overlay implementation"}
