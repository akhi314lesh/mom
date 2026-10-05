"""
pipeline/continuity.py — Cross-Meeting ActionItem Tracking & Continuity Resolver.

Implements Phase 6 meeting continuity:
- Identifies active action items from earlier meetings (originating_meeting_id != current_meeting_id).
- Scans current meeting's transcript, semantic events, and decisions for updates to those items.
- Updates ActionItem.status and sets ActionItem.last_updated_meeting_id = current_meeting_id.
- Attaches an immutable Evidence record (source_type="CONTINUITY_UPDATE") preserving the provenance chain.
- Broadcasts WebSocket notification ACTION_CONTINUITY_UPDATED.
"""
import uuid
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.actions import ActionItem, ActionItemStatus
from app.models.evidence import Evidence
from app.models.transcript import TranscriptSegment
from app.models.semantic import SemanticEvent
from app.models.meeting import Meeting
from app.models.participant import Participant
from app.api.ws import manager as ws_manager


class ContinuityResolver:
    """
    Resolves action item lifecycle and status updates across meetings.
    """

    # Keyword patterns indicative of status transitions
    STATUS_PATTERNS = {
        ActionItemStatus.COMPLETED: [
            r"\b(completed|done|finished|shipped|closed|resolved|delivered|fixed)\b",
            r"\balready (done|finished|shipped|fixed)\b",
            r"\bwe finished\b",
        ],
        ActionItemStatus.IN_PROGRESS: [
            r"\b(in progress|working on|actively working|underway|started|ongoing)\b",
            r"\bcurrently (doing|implementing|building)\b",
        ],
        ActionItemStatus.BLOCKED: [
            r"\b(blocked|stuck|waiting on|dependency on|pending approval|held up)\b",
            r"\bcan't proceed\b",
        ],
        ActionItemStatus.CANCELLED: [
            r"\b(cancelled|abandoned|dropped|no longer needed|won't do|scrapped)\b",
        ],
    }

    async def resolve_meeting_continuity(
        self, db: AsyncSession, current_meeting_id: str
    ) -> List[Dict[str, Any]]:
        """
        Scans previous active action items and updates their status if discussed
        in the current meeting.
        """
        updates: List[Dict[str, Any]] = []

        # 1. Fetch earlier active action items
        earlier_actions_res = await db.execute(
            select(ActionItem).where(
                and_(
                    ActionItem.originating_meeting_id != current_meeting_id,
                    ActionItem.status.in_([
                        ActionItemStatus.PENDING,
                        ActionItemStatus.IN_PROGRESS,
                        ActionItemStatus.BLOCKED,
                    ]),
                )
            )
        )
        earlier_actions = earlier_actions_res.scalars().all()
        if not earlier_actions:
            return updates

        # 2. Fetch current meeting segments and semantic events
        seg_res = await db.execute(
            select(TranscriptSegment)
            .where(TranscriptSegment.meeting_id == current_meeting_id)
            .order_by(TranscriptSegment.start_ms)
        )
        segments = seg_res.scalars().all()

        sem_res = await db.execute(
            select(SemanticEvent)
            .where(SemanticEvent.meeting_id == current_meeting_id)
            .order_by(SemanticEvent.start_ms)
        )
        semantic_events = sem_res.scalars().all()

        full_text = " ".join(s.text.lower() for s in segments)
        event_texts = [e.text.lower() for e in semantic_events]

        for action in earlier_actions:
            task_clean = action.task.lower().strip()
            # Extract key topic words (length > 3, exclude stop words)
            task_keywords = [
                w for w in re.findall(r"\b\w+\b", task_clean)
                if len(w) > 3 and w not in {"with", "that", "this", "from", "have", "make", "need", "should", "will", "must", "task", "item"}
            ]

            if not task_keywords:
                continue

            # Check if task keywords appear together in any segment or event
            matching_segment: Optional[TranscriptSegment] = None
            detected_status: Optional[str] = None
            evidence_snippet: str = ""

            # Check segments first
            for seg in segments:
                s_text = seg.text.lower()
                matches = sum(1 for kw in task_keywords if kw in s_text)
                # If >= 50% of key words appear in this segment, look for status keywords
                if matches >= max(1, len(task_keywords) // 2):
                    for status_enum, patterns in self.STATUS_PATTERNS.items():
                        if any(re.search(pat, s_text) for pat in patterns):
                            matching_segment = seg
                            detected_status = status_enum
                            evidence_snippet = seg.text
                            break
                if detected_status:
                    break

            # If not in segments, check semantic events
            if not detected_status:
                for event in semantic_events:
                    e_text = event.text.lower()
                    matches = sum(1 for kw in task_keywords if kw in e_text)
                    if matches >= max(1, len(task_keywords) // 2):
                        for status_enum, patterns in self.STATUS_PATTERNS.items():
                            if any(re.search(pat, e_text) for pat in patterns):
                                detected_status = status_enum
                                evidence_snippet = event.text
                                break
                    if detected_status:
                        break

            # Apply status update if found and distinct from current status
            if detected_status and detected_status != action.status:
                old_status = action.status
                action.status = detected_status
                action.last_updated_meeting_id = current_meeting_id

                # Create immutable continuity Evidence record
                ev_id = str(uuid.uuid4())
                ev = Evidence(
                    id=ev_id,
                    meeting_id=current_meeting_id,
                    segment_id=matching_segment.id if matching_segment else None,
                    source_type="CONTINUITY_UPDATE",
                    source_modality="TRANSCRIPT" if matching_segment else "MANUAL",
                    timestamp_ms=matching_segment.start_ms if matching_segment else 0,
                    raw_text=f"Action item '{action.task}' updated from {old_status} to {detected_status}: \"{evidence_snippet}\"",
                    confidence=0.92,
                    is_immutable=True,
                )
                db.add(ev)

                # Append to action evidence_ids
                cur_evs = list(action.evidence_ids or [])
                if ev_id not in cur_evs:
                    cur_evs.append(ev_id)
                action.evidence_ids = cur_evs

                update_record = {
                    "action_id": action.id,
                    "task": action.task,
                    "old_status": old_status,
                    "new_status": detected_status,
                    "originating_meeting_id": action.originating_meeting_id,
                    "last_updated_meeting_id": current_meeting_id,
                    "evidence_id": ev_id,
                    "evidence_snippet": evidence_snippet,
                }
                updates.append(update_record)

                # Broadcast via WebSocket
                await ws_manager.broadcast(
                    current_meeting_id,
                    {
                        "type": "ACTION_CONTINUITY_UPDATED",
                        "update": update_record,
                    },
                )

        if updates:
            await db.commit()

        return updates

    async def get_action_continuity_history(
        self, db: AsyncSession, action_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Returns full cross-meeting lineage and evidence chain for an ActionItem.
        """
        act_res = await db.execute(select(ActionItem).where(ActionItem.id == action_id))
        action = act_res.scalar_one_or_none()
        if not action:
            return None

        # Fetch originating meeting
        orig_res = await db.execute(select(Meeting).where(Meeting.id == action.originating_meeting_id))
        orig_meeting = orig_res.scalar_one_or_none()

        # Fetch last updated meeting if different
        last_meeting = None
        if action.last_updated_meeting_id and action.last_updated_meeting_id != action.originating_meeting_id:
            last_res = await db.execute(select(Meeting).where(Meeting.id == action.last_updated_meeting_id))
            last_meeting = last_res.scalar_one_or_none()

        # Fetch owner
        owner = None
        if action.owner_id:
            owner_res = await db.execute(select(Participant).where(Participant.id == action.owner_id))
            owner = owner_res.scalar_one_or_none()

        # Fetch evidence records
        evidence_records = []
        if action.evidence_ids:
            ev_res = await db.execute(select(Evidence).where(Evidence.id.in_(action.evidence_ids)))
            for ev in ev_res.scalars().all():
                evidence_records.append({
                    "id": ev.id,
                    "meeting_id": ev.meeting_id,
                    "source_type": ev.source_type,
                    "raw_text": ev.raw_text,
                    "confidence": ev.confidence,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                })

        return {
            "id": action.id,
            "task": action.task,
            "status": action.status,
            "priority": action.priority,
            "deadline": str(action.deadline) if action.deadline else None,
            "confidence": action.confidence,
            "owner": {"id": owner.id, "name": owner.name, "role": owner.role} if owner else None,
            "originating_meeting": {
                "id": orig_meeting.id,
                "title": orig_meeting.title,
                "date": str(orig_meeting.date),
            } if orig_meeting else {"id": action.originating_meeting_id},
            "last_updated_meeting": {
                "id": last_meeting.id,
                "title": last_meeting.title,
                "date": str(last_meeting.date),
            } if last_meeting else None,
            "evidence_chain": evidence_records,
        }

    async def list_cross_meeting_actions(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Lists all cross-meeting actions enriched with meeting titles and owner details.
        """
        q = select(ActionItem)
        if status:
            q = q.where(ActionItem.status == status)
        if owner_id:
            q = q.where(ActionItem.owner_id == owner_id)

        result = await db.execute(q.order_by(ActionItem.status, ActionItem.originating_meeting_id))
        actions = result.scalars().all()

        # Collect meeting IDs and owner IDs for bulk lookup
        meeting_ids = set()
        owner_ids = set()
        for a in actions:
            if a.originating_meeting_id:
                meeting_ids.add(a.originating_meeting_id)
            if a.last_updated_meeting_id:
                meeting_ids.add(a.last_updated_meeting_id)
            if a.owner_id:
                owner_ids.add(a.owner_id)

        meeting_map: Dict[str, Meeting] = {}
        if meeting_ids:
            m_res = await db.execute(select(Meeting).where(Meeting.id.in_(list(meeting_ids))))
            for m in m_res.scalars().all():
                meeting_map[m.id] = m

        owner_map: Dict[str, Participant] = {}
        if owner_ids:
            p_res = await db.execute(select(Participant).where(Participant.id.in_(list(owner_ids))))
            for p in p_res.scalars().all():
                owner_map[p.id] = p

        enriched: List[Dict[str, Any]] = []
        for a in actions:
            orig_m = meeting_map.get(a.originating_meeting_id)
            last_m = meeting_map.get(a.last_updated_meeting_id) if a.last_updated_meeting_id else None
            p = owner_map.get(a.owner_id) if a.owner_id else None

            enriched.append({
                "id": a.id,
                "task": a.task,
                "status": a.status,
                "priority": a.priority,
                "deadline": str(a.deadline) if a.deadline else None,
                "confidence": a.confidence,
                "review_state": a.review_state,
                "owner_id": a.owner_id,
                "owner_name": p.name if p else None,
                "originating_meeting_id": a.originating_meeting_id,
                "originating_meeting_title": orig_m.title if orig_m else a.originating_meeting_id[:8],
                "originating_meeting_date": str(orig_m.date) if orig_m else None,
                "last_updated_meeting_id": a.last_updated_meeting_id,
                "last_updated_meeting_title": last_m.title if last_m else None,
                "evidence_count": len(a.evidence_ids or []),
            })

        return enriched


continuity_resolver = ContinuityResolver()
