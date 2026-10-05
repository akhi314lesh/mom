"""
pipeline/query_engine.py — Natural Language Query Engine with Evidence Grounding (Phase 7).

Strict Architectural Invariant:
- Every answer produced must be grounded in verifiable Evidence records.
- Hallucination or answering without grounding is strictly prohibited.
- If evidence is absent, the system must set grounded=False, confidence=0.0,
  and state that no supporting evidence exists in meeting records.
"""
import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transcript import TranscriptSegment
from app.models.decisions import Decision
from app.models.actions import ActionItem
from app.models.contradictions import Contradiction
from app.models.marks import UserMark
from app.models.knowledge import KnowledgeItem, TerminologyEntry
from app.models.participant import Participant, Speaker
from app.models.meeting import Meeting
from app.pipeline.llm.llm_adapter import get_llm_adapter


class AnswerSource(BaseModel):
    source_id: str
    source_type: str  # TRANSCRIPT | DECISION | ACTION_ITEM | CONTRADICTION | USER_MARK | KNOWLEDGE_ITEM
    quote: str
    timestamp_ms: Optional[int] = None
    speaker_name: Optional[str] = None
    meeting_id: Optional[str] = None
    meeting_title: Optional[str] = None
    confidence: float = 1.0


class MeetingQueryAnswer(BaseModel):
    query: str
    answer: str
    confidence: float
    grounded: bool
    query_type: str
    sources: List[AnswerSource] = Field(default_factory=list)


class QueryEngine:
    """
    Classifies queries, retrieves matching evidence, and synthesizes grounded answers.
    """

    def classify_query(self, query: str) -> str:
        """
        Classifies user query intent using robust word boundary matching.
        """
        q = query.lower()
        if any(re.search(rf"\b{re.escape(w)}\b", q) for w in ("who agreed", "who is doing", "who owns", "assigned to", "who will", "action item", "task", "owner")):
            return "ACTION_OWNER"
        elif any(re.search(rf"\b{re.escape(w)}\b", q) for w in ("decide", "decision", "decisions", "choice", "choose", "framework", "database", "consensus")):
            return "DECISION_STATUS"
        elif any(re.search(rf"\b{re.escape(w)}\b", q) for w in ("disagree", "disagreements", "contradict", "contradiction", "conflict", "conflicts", "oppose", "reversal", "dissent")):
            return "CONTRADICTION"
        elif any(re.search(rf"\b{re.escape(w)}\b", q) for w in ("when did", "when was", "timeline", "mark", "moment", "flag", "flagged")):
            return "TIMELINE"
        elif any(re.search(rf"\b{re.escape(w)}\b", q) for w in ("what is", "meaning of", "define", "term", "acronym", "wasapi", "mom")):
            return "FACTUAL"
        return "GENERAL"

    async def query(
        self,
        db: AsyncSession,
        query_text: str,
        meeting_id: Optional[str] = None,
    ) -> MeetingQueryAnswer:
        """
        Executes a natural language query with strict evidence grounding.
        """
        query_type = self.classify_query(query_text)
        sources: List[AnswerSource] = []

        # Extract meaningful search keywords (length > 2, exclude stop words)
        stop_words = {
            "what", "were", "where", "which", "there", "about", "would", "could", "should",
            "have", "from", "with", "that", "this", "then", "into", "their", "will", "does",
            "been", "make", "when", "who", "whom", "whose", "how", "any", "some", "the", "and", "for", "did"
        }
        meta_words = {
            "decision", "decisions", "decide", "decided", "task", "tasks", "action", "items", "item",
            "meeting", "meetings", "made", "agreed", "discussed", "tell", "show", "list", "all", "our",
            "conflict", "conflicts", "disagreement", "disagreements", "contradiction", "contradictions",
            "reversal", "reversals", "dissent", "oppose"
        }
        tokens = [
            w for w in re.findall(r"\b\w+\b", query_text.lower())
            if len(w) > 2 and w not in stop_words
        ]
        # Specific subject tokens excluding broad category names
        specific_tokens = [w for w in tokens if w not in meta_words]

        def _matches(text: str, targets: List[str]) -> bool:
            if not targets:
                return True
            lower_text = text.lower()
            return any(t in lower_text or t.rstrip('s') in lower_text for t in targets)

        # 1. Fetch meeting title map for source citations
        meeting_title_map: Dict[str, str] = {}
        m_res = await db.execute(select(Meeting))
        for m in m_res.scalars().all():
            meeting_title_map[m.id] = m.title

        # 2. Fetch participant name map
        p_res = await db.execute(select(Participant))
        part_name_map = {p.id: p.name for p in p_res.scalars().all()}

        # 3. Retrieve matching ActionItems
        if query_type in ("ACTION_OWNER", "GENERAL"):
            q_act = select(ActionItem)
            if meeting_id:
                q_act = q_act.where(
                    or_(
                        ActionItem.originating_meeting_id == meeting_id,
                        ActionItem.last_updated_meeting_id == meeting_id,
                    )
                )
            act_res = await db.execute(q_act)
            actions = act_res.scalars().all()
            for act in actions:
                if _matches(act.task, specific_tokens):
                    owner_name = part_name_map.get(act.owner_id, "Unassigned")
                    m_id = act.last_updated_meeting_id or act.originating_meeting_id
                    sources.append(
                        AnswerSource(
                            source_id=act.id,
                            source_type="ACTION_ITEM",
                            quote=f"Task: '{act.task}' assigned to {owner_name} (Status: {act.status}, Priority: {act.priority})",
                            timestamp_ms=act.originating_timestamp_ms or 0,
                            speaker_name=owner_name,
                            meeting_id=m_id,
                            meeting_title=meeting_title_map.get(m_id, m_id[:8]),
                            confidence=act.confidence or 0.90,
                        )
                    )

        # 4. Retrieve matching Decisions
        if query_type in ("DECISION_STATUS", "GENERAL"):
            q_dec = select(Decision)
            if meeting_id:
                q_dec = q_dec.where(Decision.meeting_id == meeting_id)
            dec_res = await db.execute(q_dec)
            decisions = dec_res.scalars().all()
            for dec in decisions:
                if _matches(dec.text, specific_tokens):
                    sources.append(
                        AnswerSource(
                            source_id=dec.id,
                            source_type="DECISION",
                            quote=f"Decision: '{dec.text}' (Status: {dec.status}, Confidence: {round(dec.confidence * 100)}%)",
                            timestamp_ms=0,
                            meeting_id=dec.meeting_id,
                            meeting_title=meeting_title_map.get(dec.meeting_id, dec.meeting_id[:8]),
                            confidence=dec.confidence or 0.92,
                        )
                    )

        # 5. Retrieve matching Contradictions
        if query_type in ("CONTRADICTION", "GENERAL"):
            q_con = select(Contradiction)
            if meeting_id:
                q_con = q_con.where(
                    or_(
                        Contradiction.meeting_id == meeting_id,
                        Contradiction.meeting_a_id == meeting_id,
                        Contradiction.meeting_b_id == meeting_id,
                    )
                )
            con_res = await db.execute(q_con)
            contradictions = con_res.scalars().all()
            for c in contradictions:
                if _matches(c.description, specific_tokens):
                    c_meeting = c.meeting_id or c.meeting_b_id or c.meeting_a_id
                    sources.append(
                        AnswerSource(
                            source_id=c.id,
                            source_type="CONTRADICTION",
                            quote=f"Contradiction: {c.description} (State: {c.review_state})",
                            timestamp_ms=0,
                            meeting_id=c_meeting,
                            meeting_title=meeting_title_map.get(c_meeting or "", ""),
                            confidence=c.confidence or 0.88,
                        )
                    )

        # 6. Retrieve matching TranscriptSegments
        q_seg = select(TranscriptSegment)
        if meeting_id:
            q_seg = q_seg.where(TranscriptSegment.meeting_id == meeting_id)
        seg_res = await db.execute(q_seg)
        segments = seg_res.scalars().all()
        for s in segments:
            s_text = s.text.lower()
            match_count = sum(1 for t in tokens if t in s_text)
            if match_count >= max(1, len(tokens) // 2):
                sources.append(
                    AnswerSource(
                        source_id=s.id,
                        source_type="TRANSCRIPT",
                        quote=s.text,
                        timestamp_ms=s.start_ms,
                        speaker_name=s.speaker_id,
                        meeting_id=s.meeting_id,
                        meeting_title=meeting_title_map.get(s.meeting_id, s.meeting_id[:8]),
                        confidence=s.asr_confidence or 0.90,
                    )
                )

        # 7. Retrieve matching Terminology & KnowledgeItems
        if query_type in ("FACTUAL", "GENERAL"):
            term_res = await db.execute(select(TerminologyEntry))
            for t in term_res.scalars().all():
                if any(tok in t.term.lower() or tok in t.canonical_meaning.lower() for tok in tokens) or not tokens:
                    sources.append(
                        AnswerSource(
                            source_id=t.id,
                            source_type="KNOWLEDGE_ITEM",
                            quote=f"Term: {t.term} — {t.canonical_meaning}",
                            confidence=t.confidence or 1.0,
                        )
                    )

        # 8. Retrieve UserMarks
        if query_type in ("TIMELINE", "GENERAL"):
            q_marks = select(UserMark)
            if meeting_id:
                q_marks = q_marks.where(UserMark.meeting_id == meeting_id)
            m_res = await db.execute(q_marks)
            for mark in m_res.scalars().all():
                sources.append(
                    AnswerSource(
                        source_id=mark.id,
                        source_type="USER_MARK",
                        quote=f"Mark Moment [{mark.event_type}]: {mark.optional_text or 'Moment marked by user'}",
                        timestamp_ms=mark.timestamp_ms,
                        confidence=1.0,
                        meeting_id=mark.meeting_id,
                    )
                )

        # -------------------------------------------------------------
        # SYNTHESIS WITH STRICT EVIDENCE GROUNDING
        # -------------------------------------------------------------
        if not sources:
            # STRICT INVARIANT: If no supporting evidence exists, return grounded=False
            return MeetingQueryAnswer(
                query=query_text,
                answer="No supporting evidence was found in the meeting records or organizational memory for this query.",
                confidence=0.0,
                grounded=False,
                query_type=query_type,
                sources=[],
            )

        # Deduplicate sources and limit to top 5 most relevant
        seen_quotes = set()
        unique_sources: List[AnswerSource] = []
        for s in sources:
            q_norm = s.quote.strip().lower()
            if q_norm not in seen_quotes:
                seen_quotes.add(q_norm)
                unique_sources.append(s)
            if len(unique_sources) >= 5:
                break

        # Generate deterministic grounded synthesis based on query type and sources
        answer_prose = self._synthesize_answer(query_text, query_type, unique_sources)
        avg_confidence = round(sum(s.confidence for s in unique_sources) / len(unique_sources), 2)

        return MeetingQueryAnswer(
            query=query_text,
            answer=answer_prose,
            confidence=avg_confidence,
            grounded=True,
            query_type=query_type,
            sources=unique_sources,
        )

    def _synthesize_answer(
        self, query: str, query_type: str, sources: List[AnswerSource]
    ) -> str:
        """
        Synthesizes natural language answer grounded directly in the cited sources.
        """
        if query_type == "ACTION_OWNER":
            action_sources = [s for s in sources if s.source_type == "ACTION_ITEM"]
            if action_sources:
                items = [s.quote for s in action_sources]
                return f"According to the meeting records, the following task ownership was established: {'; '.join(items)}."
            transcript_sources = [s for s in sources if s.source_type == "TRANSCRIPT"]
            if transcript_sources:
                quotes = '", "'.join(s.quote for s in transcript_sources)
                return f'Based on the discussion, the agreement was: "{quotes}".'

        elif query_type == "DECISION_STATUS":
            decision_sources = [s for s in sources if s.source_type == "DECISION"]
            if decision_sources:
                dec_texts = [s.quote for s in decision_sources]
                return f"The following decision(s) were recorded: {'; '.join(dec_texts)}."

        elif query_type == "CONTRADICTION":
            con_sources = [s for s in sources if s.source_type == "CONTRADICTION"]
            if con_sources:
                items = [s.quote for s in con_sources]
                return f"The consistency engine identified the following conflict(s): {'; '.join(items)}."

        elif query_type == "FACTUAL":
            k_sources = [s for s in sources if s.source_type == "KNOWLEDGE_ITEM"]
            if k_sources:
                return f"Organizational memory record: {k_sources[0].quote}."

        # General synthesis
        quotes_summary = " ".join(f'"{s.quote}"' for s in sources[:3])
        return f"Based on verified meeting evidence: {quotes_summary}"


query_engine = QueryEngine()
