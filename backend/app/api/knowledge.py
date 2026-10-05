"""
api/knowledge.py — Knowledge items, Terminology dictionary, and Organizational Memory.
"""
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.knowledge import KnowledgeItem, TerminologyEntry
from app.models.contradictions import Contradiction
from app.models.meeting import Meeting
from app.pipeline.knowledge_accretion import knowledge_accretion_engine

router = APIRouter()


@router.get("/items", summary="List knowledge items from organizational memory")
async def list_knowledge(
    verified_only: bool = False,
    item_type: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns persistent knowledge items accreted across meetings.
    """
    q = select(KnowledgeItem)
    if verified_only:
        q = q.where(KnowledgeItem.verified == True)  # noqa: E712
    if item_type and isinstance(item_type, str):
        q = q.where(KnowledgeItem.type == item_type)
    if search and isinstance(search, str):
        q = q.where(KnowledgeItem.content.ilike(f"%{search}%"))

    result = await db.execute(q.order_by(KnowledgeItem.created_at.desc()))
    items = result.scalars().all()

    return [
        {
            "id": k.id,
            "type": k.type,
            "content": k.content,
            "confidence": k.confidence,
            "verified": k.verified,
            "verification_source": k.verification_source,
            "source_meeting_ids": k.source_meeting_ids or [],
            "source_meetings_count": len(k.source_meeting_ids or []),
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in items
    ]


@router.post("/items", summary="Add manual knowledge item (verified=True, source=HUMAN)")
async def create_knowledge_item(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    content = body.get("content", "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    item_type = body.get("type", "FACT").upper()
    meeting_ids = body.get("source_meeting_ids", [])

    import uuid
    item = KnowledgeItem(
        id=str(uuid.uuid4()),
        type=item_type,
        content=content,
        source_meeting_ids=meeting_ids,
        confidence=1.0,
        verified=True,  # Explicit human entry
        verification_source="HUMAN",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "id": item.id,
        "type": item.type,
        "content": item.content,
        "verified": item.verified,
        "verification_source": item.verification_source,
    }


@router.patch("/items/{item_id}/verify", summary="Verify or reject a knowledge item (Human Action)")
async def verify_knowledge(
    item_id: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    verified = body.get("verified", True)
    item = await knowledge_accretion_engine.verify_knowledge_item(db, item_id, verified)
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    return {
        "id": item.id,
        "verified": item.verified,
        "verification_source": item.verification_source,
        "confidence": item.confidence,
    }


@router.delete("/items/{item_id}", summary="Delete a knowledge item")
async def delete_knowledge_item(
    item_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    res = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge item not found")

    await db.delete(item)
    await db.commit()
    return {"status": "deleted", "id": item_id}


@router.get("/terminology", summary="List terminology entries across organizational memory")
async def list_terminology(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    q = select(TerminologyEntry)
    if search and isinstance(search, str):
        q = q.where(
            or_(
                TerminologyEntry.term.ilike(f"%{search}%"),
                TerminologyEntry.canonical_meaning.ilike(f"%{search}%"),
            )
        )
    result = await db.execute(q.order_by(TerminologyEntry.term))
    terms = result.scalars().all()

    return [
        {
            "id": t.id,
            "term": t.term,
            "canonical_meaning": t.canonical_meaning,
            "aliases": t.aliases or [],
            "verified": t.verified,
            "confidence": t.confidence,
            "source_meeting_ids": t.source_meeting_ids or [],
            "source_meetings_count": len(t.source_meeting_ids or []),
        }
        for t in terms
    ]


@router.post("/terminology", summary="Add or update terminology entry (Human Action)")
async def upsert_terminology(
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    term_text = body.get("term", "").strip()
    if not term_text:
        raise HTTPException(status_code=400, detail="Term cannot be empty")

    res = await db.execute(select(TerminologyEntry).where(TerminologyEntry.term.ilike(term_text)))
    entry = res.scalar_one_or_none()

    if entry:
        entry.canonical_meaning = body.get("canonical_meaning", entry.canonical_meaning)
        if "aliases" in body:
            entry.aliases = body["aliases"]
        entry.verified = True
        entry.confidence = 1.0
    else:
        import uuid
        entry = TerminologyEntry(
            id=str(uuid.uuid4()),
            term=term_text,
            canonical_meaning=body.get("canonical_meaning", ""),
            aliases=body.get("aliases", []),
            source_meeting_ids=[],
            confidence=1.0,
            verified=True,
        )
        db.add(entry)

    await db.commit()
    await db.refresh(entry)
    return {
        "id": entry.id,
        "term": entry.term,
        "canonical_meaning": entry.canonical_meaning,
        "aliases": entry.aliases,
        "verified": entry.verified,
    }


@router.patch("/terminology/{term_id}/verify", summary="Verify or update terminology entry")
async def verify_term(
    term_id: str,
    body: Dict[str, Any],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    verified = body.get("verified", True)
    meaning = body.get("canonical_meaning")
    term = await knowledge_accretion_engine.verify_terminology(db, term_id, verified, meaning)
    if not term:
        raise HTTPException(status_code=404, detail="Terminology entry not found")

    return {
        "id": term.id,
        "term": term.term,
        "verified": term.verified,
        "confidence": term.confidence,
        "canonical_meaning": term.canonical_meaning,
    }


@router.post("/meetings/{meeting_id}/accrete", summary="Trigger knowledge accretion from a meeting")
async def trigger_meeting_accretion(
    meeting_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    return await knowledge_accretion_engine.accrete_from_meeting(db, meeting_id)


@router.get("/contradictions", summary="List cross-meeting decision reversals and contradictions")
async def list_cross_meeting_contradictions(
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Returns all contradictions flagged across multiple meetings (Cross-Meeting Continuity).
    """
    q = select(Contradiction).where(Contradiction.is_cross_meeting == True)  # noqa: E712
    result = await db.execute(q)
    contradictions = result.scalars().all()

    # Look up meeting titles
    meeting_ids = set()
    for c in contradictions:
        if c.meeting_a_id:
            meeting_ids.add(c.meeting_a_id)
        if c.meeting_b_id:
            meeting_ids.add(c.meeting_b_id)
        if c.meeting_id:
            meeting_ids.add(c.meeting_id)

    meetings_map: Dict[str, str] = {}
    if meeting_ids:
        m_res = await db.execute(select(Meeting).where(Meeting.id.in_(list(meeting_ids))))
        for m in m_res.scalars().all():
            meetings_map[m.id] = m.title

    return [
        {
            "id": c.id,
            "description": c.description,
            "contradiction_type": c.contradiction_type,
            "confidence": c.confidence,
            "review_state": c.review_state,
            "meeting_a_id": c.meeting_a_id,
            "meeting_a_title": meetings_map.get(c.meeting_a_id or "", c.meeting_a_id),
            "meeting_b_id": c.meeting_b_id,
            "meeting_b_title": meetings_map.get(c.meeting_b_id or "", c.meeting_b_id),
            "event_a_id": c.event_a_id,
            "event_b_id": c.event_b_id,
        }
        for c in contradictions
    ]
