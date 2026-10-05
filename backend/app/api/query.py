"""api/query.py — Ask the Meeting natural language query (Phase 7 stub)."""
from fastapi import APIRouter
router = APIRouter()

@router.post("/", summary="Ask the Meeting — natural language query")
async def ask_meeting(body: dict) -> dict:
    """
    Phase 7: full NL query with evidence grounding.
    Phase 0: returns stub indicating feature is pending.
    """
    query = body.get("query", "")
    return {
        "query": query,
        "answer": "Ask the Meeting is implemented in Phase 7.",
        "confidence": 0.0,
        "sources": [],
        "phase": "pending",
    }
