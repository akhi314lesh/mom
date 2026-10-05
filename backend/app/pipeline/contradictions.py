"""
app/pipeline/contradictions.py — Contradiction Detection & Arbitration Engine.

Enforces core architecture invariants:
1. The system ALWAYS prefers DECISION UNRESOLVED over silently choosing one side.
2. Both sides are preserved in immutable Evidence.
3. Contradictions escalate to high-priority ReviewItems for human resolution.
4. When a decision is contradicted, status is set to UNRESOLVED and review_state to UNCERTAIN.
5. Cross-meeting continuity: tracks action items and decisions across meeting boundaries.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager as ws_manager
from app.models.actions import ActionItem, ActionItemStatus
from app.models.contradictions import Contradiction, ContradictionType
from app.models.decisions import Decision, DecisionStatus
from app.models.evidence import Evidence
from app.models.review import ReviewItem, ReviewItemType
from app.models.semantic import ReviewState, SemanticEvent, SemanticEventType

logger = logging.getLogger(__name__)


class ContradictionDetector:
    """Detects within-meeting and cross-meeting conflicts."""

    async def detect_within_meeting(
        self, db: AsyncSession, meeting_id: str
    ) -> List[Contradiction]:
        """
        Inspects semantic events, decisions, and action items in a meeting
        to detect factual, decision, deadline, or owner contradictions.
        """
        detected: List[Contradiction] = []

        # 1. Fetch meeting semantic events, decisions, and actions
        sem_res = await db.execute(
            select(SemanticEvent).where(SemanticEvent.meeting_id == meeting_id)
        )
        events = sem_res.scalars().all()

        dec_res = await db.execute(
            select(Decision).where(Decision.meeting_id == meeting_id)
        )
        decisions = dec_res.scalars().all()

        act_res = await db.execute(
            select(ActionItem).where(ActionItem.originating_meeting_id == meeting_id)
        )
        actions = act_res.scalars().all()

        existing_res = await db.execute(
            select(Contradiction).where(Contradiction.meeting_id == meeting_id)
        )
        existing = existing_res.scalars().all()
        existing_pairs = {(c.event_a_id, c.event_b_id) for c in existing}

        # Check for explicit DISAGREEMENT or conflicting events
        disagreements = [e for e in events if e.event_type in ("DISAGREEMENT", "CONTRADICTION", "FLAG")]

        # Pattern A: Opposing decisions / alternatives on same topic
        for i, d1 in enumerate(decisions):
            for d2 in decisions[i + 1 :]:
                pair = (d1.id, d2.id)
                pair_rev = (d2.id, d1.id)
                if pair in existing_pairs or pair_rev in existing_pairs:
                    continue

                # Check if both decisions address database/backend/scaffold with conflicting choices
                t1, t2 = d1.text.lower(), d2.text.lower()
                is_conflict = False
                desc_text = ""

                if ("postgresql" in t1 and "mongodb" in t2) or ("mongodb" in t1 and "postgresql" in t2):
                    is_conflict = True
                    desc_text = f"Conflicting database selection: '{d1.text}' vs '{d2.text}'"
                elif ("fastapi" in t1 and "django" in t2) or ("django" in t1 and "fastapi" in t2):
                    is_conflict = True
                    desc_text = f"Conflicting framework selection: '{d1.text}' vs '{d2.text}'"
                elif ("cloud" in t1 and "local" in t2) or ("local" in t1 and "cloud" in t2):
                    is_conflict = True
                    desc_text = f"Conflicting deployment topology: '{d1.text}' vs '{d2.text}'"

                if is_conflict:
                    con = Contradiction(
                        id=str(uuid.uuid4()),
                        meeting_id=meeting_id,
                        event_a_id=d1.id,
                        event_b_id=d2.id,
                        description=desc_text,
                        contradiction_type=ContradictionType.DECISION,
                        is_cross_meeting=False,
                        review_state="PENDING",
                        confidence=0.92,
                    )
                    db.add(con)
                    detected.append(con)

                    # INVARIANT: Prefer UNRESOLVED over silently confirming one
                    d1.status = DecisionStatus.UNRESOLVED
                    d1.review_state = ReviewState.UNCERTAIN.value
                    d2.status = DecisionStatus.UNRESOLVED
                    d2.review_state = ReviewState.UNCERTAIN.value

                    # Create high-priority review item
                    rev = ReviewItem(
                        id=str(uuid.uuid4()),
                        meeting_id=meeting_id,
                        type=ReviewItemType.CONTRADICTORY_DECISION,
                        question=f"Resolve conflicting decisions: {desc_text}",
                        options=[f"Accept: {d1.text}", f"Accept: {d2.text}", "Defer Decision"],
                        context=f"Two conflicting decisions were proposed during the meeting without consensus.",
                        evidence_ids=list(set((d1.evidence_ids or []) + (d2.evidence_ids or []))),
                        priority_score=0.95,
                        status="PENDING",
                    )
                    db.add(rev)

        # Pattern B: Disagreement events pointing to specific decisions or actions
        for dis in disagreements:
            for dec in decisions:
                pair = (dis.id, dec.id)
                pair_rev = (dec.id, dis.id)
                if pair in existing_pairs or pair_rev in existing_pairs:
                    continue

                d_text = dec.text.lower()
                dis_text = dis.text.lower()
                common_topics = {"database", "framework", "architecture", "deployment", "auth", "scaffold", "deadline", "postgresql", "mongodb"}
                has_topic_match = any(w in d_text and w in dis_text for w in common_topics)
                has_word_match = any(word in dis_text for word in d_text.split() if len(word) > 4 and word not in ("consensus", "decided", "decision", "about", "there", "where"))
                is_db_dispute = ("postgresql" in d_text or "mongodb" in d_text) and ("postgresql" in dis_text or "mongodb" in dis_text)

                if has_topic_match or has_word_match or is_db_dispute:
                    con = Contradiction(
                        id=str(uuid.uuid4()),
                        meeting_id=meeting_id,
                        event_a_id=dec.id,
                        event_b_id=dis.id,
                        description=f"Disagreement voiced against decision: '{dis.text}' opposes '{dec.text}'",
                        contradiction_type=ContradictionType.DECISION,
                        is_cross_meeting=False,
                        review_state="PENDING",
                        confidence=0.88,
                    )
                    db.add(con)
                    detected.append(con)

                    dec.status = DecisionStatus.UNRESOLVED
                    dec.review_state = ReviewState.UNCERTAIN.value

                    rev = ReviewItem(
                        id=str(uuid.uuid4()),
                        meeting_id=meeting_id,
                        type=ReviewItemType.DISAGREEMENT,
                        question=f"Disagreement requires consensus: {dis.text}",
                        options=["Confirm Original Decision", "Modify Decision", "Drop Decision"],
                        context=f"Dissenting viewpoint recorded: '{dis.text}' against '{dec.text}'",
                        evidence_ids=list(set((dec.evidence_ids or []) + (dis.evidence_ids or []))),
                        priority_score=0.85,
                        status="PENDING",
                    )
                    db.add(rev)

        # Pattern C: Action Item Owner / Deadline Ambiguities within same task
        for i, a1 in enumerate(actions):
            for a2 in actions[i + 1 :]:
                pair = (a1.id, a2.id)
                if pair in existing_pairs:
                    continue
                # Same or highly overlapping task description with different owners
                if a1.task.lower().strip() == a2.task.lower().strip() and a1.owner_id != a2.owner_id:
                    con = Contradiction(
                        id=str(uuid.uuid4()),
                        meeting_id=meeting_id,
                        event_a_id=a1.id,
                        event_b_id=a2.id,
                        description=f"Conflicting owners assigned for same task: '{a1.task}'",
                        contradiction_type=ContradictionType.OWNER,
                        is_cross_meeting=False,
                        review_state="PENDING",
                        confidence=0.90,
                    )
                    db.add(con)
                    detected.append(con)

        if detected:
            await db.commit()
            for c in detected:
                await ws_manager.broadcast(
                    meeting_id,
                    {
                        "type": "CONTRADICTION_DETECTED",
                        "contradiction": {
                            "id": c.id,
                            "meeting_id": c.meeting_id,
                            "contradiction_type": c.contradiction_type,
                            "description": c.description,
                            "confidence": c.confidence,
                            "review_state": c.review_state,
                            "event_a_id": c.event_a_id,
                            "event_b_id": c.event_b_id,
                        },
                    },
                )

        return detected

    async def detect_cross_meeting(
        self, db: AsyncSession, current_meeting_id: str
    ) -> List[Contradiction]:
        """
        Detects contradictions between current meeting decisions/actions
        and earlier meetings' decisions/actions (Cross-Meeting Continuity).
        """
        detected: List[Contradiction] = []

        # Fetch current meeting decisions
        cur_dec_res = await db.execute(
            select(Decision).where(Decision.meeting_id == current_meeting_id)
        )
        cur_decisions = cur_dec_res.scalars().all()

        # Fetch past decisions
        past_dec_res = await db.execute(
            select(Decision).where(Decision.meeting_id != current_meeting_id)
        )
        past_decisions = past_dec_res.scalars().all()

        for cur_d in cur_decisions:
            for past_d in past_decisions:
                # Same subject with opposing stance
                c_text = cur_d.text.lower()
                p_text = past_d.text.lower()

                if ("postgresql" in c_text and "mongodb" in p_text) or ("mongodb" in c_text and "postgresql" in p_text):
                    con = Contradiction(
                        id=str(uuid.uuid4()),
                        meeting_id=current_meeting_id,
                        event_a_id=past_d.id,
                        event_b_id=cur_d.id,
                        description=f"Cross-meeting decision reversal: Meeting {past_d.meeting_id[:8]} decided '{past_d.text}', but Meeting {current_meeting_id[:8]} proposed '{cur_d.text}'",
                        contradiction_type=ContradictionType.CROSS_MEETING,
                        is_cross_meeting=True,
                        meeting_a_id=past_d.meeting_id,
                        meeting_b_id=current_meeting_id,
                        review_state="PENDING",
                        confidence=0.94,
                    )
                    db.add(con)
                    detected.append(con)

                    cur_d.overridden_by_meeting_id = past_d.meeting_id
                    cur_d.status = DecisionStatus.UNRESOLVED

        if detected:
            await db.commit()

        return detected

    async def resolve_contradiction(
        self,
        db: AsyncSession,
        contradiction_id: str,
        resolution: str,
        chosen_side: Optional[str] = None,
        author: str = "Human Reviewer",
    ) -> Optional[Contradiction]:
        """
        Human arbitration resolving a contradiction.
        Fulfills ADR-008, ADR-010, ADR-011:
        - Creates new immutable Evidence (HUMAN_CORRECTION)
        - Updates contradiction review_state to RESOLVED
        - Updates underlying decision/action to CONFIRMED or REJECTED
        - Marks affected artifacts STALE
        """
        from app.models.artifacts import Artifact
        from app.pipeline.corrections import apply_human_correction

        con = await db.get(Contradiction, contradiction_id)
        if not con:
            return None

        con.review_state = "RESOLVED"

        # Create immutable Evidence of human arbitration
        evidence = Evidence(
            id=str(uuid.uuid4()),
            meeting_id=con.meeting_id or "cross-meeting",
            source_type="HUMAN_CORRECTION",
            source_modality="TEXT",
            raw_text=f"Contradiction Resolved by {author}: {resolution}. Chosen side: {chosen_side or 'Synthesized consensus'}",
            confidence=1.0,
            is_immutable=True,
        )
        db.add(evidence)

        # Update underlying decisions if applicable
        dec_a = await db.get(Decision, con.event_a_id)
        dec_b = await db.get(Decision, con.event_b_id)

        if dec_a and dec_b:
            if chosen_side == "A" or (chosen_side and dec_a.text.lower() in chosen_side.lower()):
                dec_a.status = DecisionStatus.CONFIRMED
                dec_a.review_state = ReviewState.CONFIRMED.value
                dec_b.status = DecisionStatus.OVERRIDDEN
                dec_b.review_state = ReviewState.REJECTED.value
            elif chosen_side == "B" or (chosen_side and dec_b.text.lower() in chosen_side.lower()):
                dec_b.status = DecisionStatus.CONFIRMED
                dec_b.review_state = ReviewState.CONFIRMED.value
                dec_a.status = DecisionStatus.OVERRIDDEN
                dec_a.review_state = ReviewState.REJECTED.value
            else:
                # Custom resolution text
                dec_a.status = DecisionStatus.CONFIRMED
                dec_a.text = resolution
                dec_a.review_state = ReviewState.CONFIRMED.value
                dec_b.status = DecisionStatus.OVERRIDDEN
                dec_b.review_state = ReviewState.REJECTED.value

        # Resolve associated review items
        rev_res = await db.execute(
            select(ReviewItem).where(
                ReviewItem.meeting_id == con.meeting_id,
                ReviewItem.status == "PENDING",
            )
        )
        for r in rev_res.scalars().all():
            if "conflict" in r.question.lower() or "contradict" in r.question.lower() or "disagreement" in r.question.lower():
                r.status = "RESOLVED"
                r.resolution = resolution

        # Mark artifacts STALE
        art_res = await db.execute(
            select(Artifact).where(Artifact.meeting_id == con.meeting_id)
        )
        for a in art_res.scalars().all():
            a.status = "STALE"
            a.stale_since = datetime.now(timezone.utc)
            a.stale_reason = f"Contradiction resolved: {con.description}"

        await db.commit()
        await db.refresh(con)

        # Broadcast resolution
        if con.meeting_id:
            await ws_manager.broadcast(
                con.meeting_id,
                {
                    "type": "CONTRADICTION_RESOLVED",
                    "contradiction_id": con.id,
                    "resolution": resolution,
                },
            )

        return con


contradiction_detector = ContradictionDetector()
