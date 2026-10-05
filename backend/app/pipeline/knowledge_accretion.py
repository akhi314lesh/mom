"""
pipeline/knowledge_accretion.py — KnowledgeItem & Terminology Accretion Engine.

Implements Phase 6 persistent organizational memory:
- Accretes confirmed decisions, architectural patterns, facts, and terminology.
- Deduplicates across meetings, tracking source_meeting_ids.
- Strict Invariant:
  KnowledgeItem.verified = True requires EITHER:
    - verification_source = HUMAN (explicit user confirmation)
    - OR system confidence >= settings.min_auto_accept_confidence (0.85)
  verification_source = INFERRED is NEVER sufficient to set verified = True.
"""
import uuid
import re
from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import KnowledgeItem, TerminologyEntry
from app.models.decisions import Decision, DecisionStatus
from app.models.transcript import TranscriptSegment
from app.models.semantic import SemanticEvent
from app.config import settings


# Common domain terms and acronyms to detect if present in transcripts
KNOWN_DOMAIN_TERMS = {
    "mom": ("Minutes of Meeting", ["MoM", "meeting minutes"]),
    "fastapi": ("Python async web framework for high-performance APIs", ["FastAPI"]),
    "postgresql": ("Open-source relational database management system", ["PostgreSQL", "Postgres"]),
    "mongodb": ("Document-oriented NoSQL database system", ["MongoDB", "Mongo"]),
    "wasapi": ("Windows Audio Session API used for loopback system audio capture", ["WASAPI"]),
    "asr": ("Automatic Speech Recognition engine", ["ASR", "speech-to-text"]),
    "diarization": ("Process of partitioning audio stream into speaker segments", ["Speaker Diarization"]),
    "jwt": ("JSON Web Token for stateless authenticated sessions", ["JWT"]),
    "alembic": ("Lightweight database migration tool for SQLAlchemy", ["Alembic"]),
    "weasyprint": ("Document factory converting HTML/CSS into PDF", ["WeasyPrint"]),
    "pywebview": ("Lightweight cross-platform wrapper around webview component", ["PyWebView"]),
}


class KnowledgeAccretionEngine:
    """
    Accretes persistent facts, confirmed decisions, and terminology into organizational memory.
    """

    async def accrete_from_meeting(
        self, db: AsyncSession, meeting_id: str
    ) -> Dict[str, Any]:
        """
        Extracts and accretes knowledge items and terminology from a meeting.
        """
        accreted_items: List[KnowledgeItem] = []
        accreted_terms: List[TerminologyEntry] = []

        # 1. Fetch confirmed decisions from meeting
        dec_res = await db.execute(
            select(Decision).where(Decision.meeting_id == meeting_id)
        )
        decisions = dec_res.scalars().all()

        for dec in decisions:
            # We accrete decisions that are not UNRESOLVED
            if dec.status == DecisionStatus.UNRESOLVED:
                continue

            content = f"Decision: {dec.text}"
            item_type = "DECISION"
            confidence = dec.confidence or 0.85

            # Strict Invariant Evaluation:
            # verified=True requires verification_source=HUMAN or confidence >= min_auto_accept_confidence
            is_high_conf = confidence >= settings.min_auto_accept_confidence
            verified = is_high_conf
            source = "SYSTEM" if is_high_conf else "INFERRED"

            # Check if this decision already exists in knowledge items
            existing_res = await db.execute(
                select(KnowledgeItem).where(
                    KnowledgeItem.type == item_type,
                    KnowledgeItem.content.ilike(f"%{dec.text[:40]}%"),
                )
            )
            existing = existing_res.scalar_one_or_none()

            if existing:
                # Add meeting_id if not present
                s_ids = list(existing.source_meeting_ids or [])
                if meeting_id not in s_ids:
                    s_ids.append(meeting_id)
                    existing.source_meeting_ids = s_ids
                # Boost confidence slightly
                existing.confidence = min(0.99, existing.confidence + 0.05)
                accreted_items.append(existing)
            else:
                k_item = KnowledgeItem(
                    id=str(uuid.uuid4()),
                    type=item_type,
                    content=content,
                    source_meeting_ids=[meeting_id],
                    confidence=confidence,
                    verified=verified,
                    verification_source=source,
                )
                db.add(k_item)
                accreted_items.append(k_item)

        # 2. Extract domain terminology from transcript segments
        seg_res = await db.execute(
            select(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id)
        )
        segments = seg_res.scalars().all()
        full_text = " ".join(s.text for s in segments)
        lower_text = full_text.lower()

        for term_key, (canon_meaning, aliases) in KNOWN_DOMAIN_TERMS.items():
            if term_key in lower_text or any(a.lower() in lower_text for a in aliases):
                # Check if already in DB
                t_res = await db.execute(
                    select(TerminologyEntry).where(TerminologyEntry.term.ilike(aliases[0]))
                )
                existing_t = t_res.scalar_one_or_none()

                if existing_t:
                    t_s_ids = list(existing_t.source_meeting_ids or [])
                    if meeting_id not in t_s_ids:
                        t_s_ids.append(meeting_id)
                        existing_t.source_meeting_ids = t_s_ids
                    accreted_terms.append(existing_t)
                else:
                    new_t = TerminologyEntry(
                        id=str(uuid.uuid4()),
                        term=aliases[0],
                        canonical_meaning=canon_meaning,
                        aliases=aliases[1:],
                        source_meeting_ids=[meeting_id],
                        confidence=0.90,
                        verified=True,  # Built-in curated terms are pre-verified
                    )
                    db.add(new_t)
                    accreted_terms.append(new_t)

        # 3. Detect uppercase acronyms mentioned in meetings (e.g. WASAPI, CI/CD, ASR)
        acronym_candidates = set(re.findall(r"\b[A-Z]{2,6}\b", full_text))
        for acr in acronym_candidates:
            if acr.lower() in KNOWN_DOMAIN_TERMS or acr in {"THE", "AND", "FOR", "NOT", "YES", "DOC", "PDF", "API"}:
                continue
            # Check if this acronym exists as a KnowledgeItem or TerminologyEntry
            t_res = await db.execute(
                select(TerminologyEntry).where(TerminologyEntry.term == acr)
            )
            if not t_res.scalar_one_or_none():
                # Add inferred Terminology candidate
                inferred_t = TerminologyEntry(
                    id=str(uuid.uuid4()),
                    term=acr,
                    canonical_meaning=f"Acronym used in meeting {meeting_id[:8]}",
                    aliases=[],
                    source_meeting_ids=[meeting_id],
                    confidence=0.60,
                    verified=False,  # INFERRED is never verified without human review
                )
                db.add(inferred_t)
                accreted_terms.append(inferred_t)

        await db.commit()

        return {
            "accreted_knowledge_items": len(accreted_items),
            "accreted_terminology": len(accreted_terms),
        }

    async def verify_knowledge_item(
        self, db: AsyncSession, item_id: str, verified: bool = True
    ) -> Optional[KnowledgeItem]:
        """
        Human confirmation flow for a KnowledgeItem.
        Strict invariant: When confirmed by a human, verification_source=HUMAN and confidence=1.0.
        """
        res = await db.execute(select(KnowledgeItem).where(KnowledgeItem.id == item_id))
        item = res.scalar_one_or_none()
        if not item:
            return None

        item.verified = verified
        if verified:
            item.verification_source = "HUMAN"
            item.confidence = 1.0
        else:
            item.verification_source = "INFERRED"
            item.confidence = max(0.5, item.confidence * 0.8)

        await db.commit()
        await db.refresh(item)
        return item

    async def verify_terminology(
        self,
        db: AsyncSession,
        term_id: str,
        verified: bool = True,
        canonical_meaning: Optional[str] = None,
    ) -> Optional[TerminologyEntry]:
        """
        Human verification and correction flow for a TerminologyEntry.
        """
        res = await db.execute(select(TerminologyEntry).where(TerminologyEntry.id == term_id))
        term = res.scalar_one_or_none()
        if not term:
            return None

        term.verified = verified
        term.confidence = 1.0 if verified else 0.5
        if canonical_meaning:
            term.canonical_meaning = canonical_meaning

        await db.commit()
        await db.refresh(term)
        return term


knowledge_accretion_engine = KnowledgeAccretionEngine()
