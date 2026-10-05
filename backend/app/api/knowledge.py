"""api/knowledge.py — Knowledge items and terminology."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.knowledge import KnowledgeItem, TerminologyEntry

router = APIRouter()

@router.get("/items", summary="List knowledge items")
async def list_knowledge(verified_only: bool = False, db: AsyncSession = Depends(get_db)) -> list[dict]:
    q = select(KnowledgeItem)
    if verified_only:
        q = q.where(KnowledgeItem.verified == True)  # noqa: E712
    result = await db.execute(q.order_by(KnowledgeItem.created_at.desc()))
    return [{"id": k.id, "type": k.type, "content": k.content, "confidence": k.confidence, "verified": k.verified, "verification_source": k.verification_source} for k in result.scalars().all()]

@router.get("/terminology", summary="List terminology entries")
async def list_terminology(db: AsyncSession = Depends(get_db)) -> list[dict]:
    result = await db.execute(select(TerminologyEntry).order_by(TerminologyEntry.term))
    return [{"id": t.id, "term": t.term, "canonical_meaning": t.canonical_meaning, "aliases": t.aliases, "verified": t.verified, "confidence": t.confidence} for t in result.scalars().all()]

@router.post("/terminology", summary="Add or update terminology entry")
async def upsert_terminology(body: dict, db: AsyncSession = Depends(get_db)) -> dict:
    """User-supplied terminology corrections are verified=True, source=HUMAN."""
    entry = TerminologyEntry(
        term=body.get("term", ""),
        canonical_meaning=body.get("canonical_meaning", ""),
        aliases=body.get("aliases", []),
        confidence=1.0,
        verified=True,  # user-supplied
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "term": entry.term}
