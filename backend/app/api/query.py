"""
api/query.py — Ask the Meeting natural language query endpoint (Phase 7).

Every answer is strictly grounded in retrieved evidence items with confidence
scoring, verbatim quotes, and timestamp markers.
"""
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.pipeline.query_engine import query_engine, MeetingQueryAnswer

router = APIRouter()


@router.post("/", summary="Ask the Meeting — natural language query with evidence grounding")
async def ask_meeting(
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Executes a natural language query against meeting records or organizational memory.
    Strict Invariant: Every answer is grounded in retrieved evidence. If no supporting
    evidence exists, grounded=False is returned.
    """
    query_text = body.get("query", "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    meeting_id = body.get("meeting_id")
    answer_obj: MeetingQueryAnswer = await query_engine.query(
        db=db,
        query_text=query_text,
        meeting_id=meeting_id,
    )
    return answer_obj.model_dump()


@router.post("/meeting/{meeting_id}", summary="Ask questions specific to a single meeting")
async def ask_single_meeting(
    meeting_id: str,
    body: Dict[str, Any] = Body(...),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Scopes query specifically to one meeting's transcript, decisions, actions, and marks.
    """
    query_text = body.get("query", "").strip()
    if not query_text:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    answer_obj: MeetingQueryAnswer = await query_engine.query(
        db=db,
        query_text=query_text,
        meeting_id=meeting_id,
    )
    return answer_obj.model_dump()
