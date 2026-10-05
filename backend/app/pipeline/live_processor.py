"""
app/pipeline/live_processor.py — Live Capture & Streaming Semantic Processor.

Implements Phase 5 Live Capture Mode:
- Ingests streaming speech segments / chunks in real-time.
- Performs incremental semantic classification (ideas, candidate decisions, action commitments, disagreements).
- Coordinates immediate contradiction detection when conflicting statements or disagreement signals arrive.
- Broadcasts real-time events to the desktop overlay and workspace timeline via WebSocket.
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager as ws_manager
from app.models.actions import ActionItem, ActionItemPriority, ActionItemStatus
from app.models.decisions import Decision, DecisionStatus
from app.models.evidence import Evidence
from app.models.semantic import ReviewState, SemanticEvent, SemanticEventType
from app.models.transcript import TranscriptSegment
from app.pipeline.contradictions import contradiction_detector

logger = logging.getLogger(__name__)


class LiveCaptureProcessor:
    """Processes incremental real-time utterances and user marks during live meetings."""

    async def process_utterance(
        self,
        db: AsyncSession,
        meeting_id: str,
        text: str,
        start_ms: int,
        end_ms: int,
        speaker_id: Optional[str] = None,
        speaker_name: Optional[str] = None,
        confidence: float = 0.92,
    ) -> Dict[str, Any]:
        """
        Process a single spoken utterance in real-time during live capture.
        Creates TranscriptSegment, Evidence, and any inferred SemanticEvents.
        """
        # 1. Create TranscriptSegment
        seg_id = str(uuid.uuid4())
        seg = TranscriptSegment(
            id=seg_id,
            meeting_id=meeting_id,
            speaker_id=speaker_id,
            start_ms=start_ms,
            end_ms=end_ms,
            text=text,
            language="en",
            asr_confidence=confidence,
            is_edited=False,
            source_modality="AUDIO",
        )
        db.add(seg)

        # 2. Create immutable Evidence
        ev_id = str(uuid.uuid4())
        ev = Evidence(
            id=ev_id,
            meeting_id=meeting_id,
            segment_id=seg_id,
            source_type="TRANSCRIPT",
            source_modality="AUDIO",
            timestamp_ms=start_ms,
            raw_text=text,
            confidence=confidence,
            is_immutable=True,
        )
        db.add(ev)
        await db.flush()

        # 3. Incremental heuristic & semantic classification
        lower = text.lower()
        extracted_events: List[SemanticEvent] = []

        # Check for disagreement / contradiction signals
        is_disagreement = any(
            phrase in lower
            for phrase in (
                "i disagree",
                "not sure about that",
                "i don't agree",
                "that won't work",
                "instead of",
                "prefer mongodb over",
                "prefer postgresql over",
                "cannot meet that deadline",
                "we should not",
                "push back",
            )
        )

        is_decision = any(
            phrase in lower
            for phrase in (
                "we have decided",
                "agreed that",
                "let's go with",
                "decision is to",
                "we will use",
                "approved",
                "consensus is",
            )
        )

        is_action = any(
            phrase in lower
            for phrase in (
                "i will handle",
                "i'll take care of",
                "action item for",
                "by next week",
                "will prepare",
                "assigned to",
            )
        )

        if is_disagreement:
            sem_ev = SemanticEvent(
                id=str(uuid.uuid4()),
                meeting_id=meeting_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                event_type=SemanticEventType.DISAGREEMENT.value,
                evidence_ids=[ev_id],
                confidence=0.88,
                extraction_stage="LIVE_PERCEPTION",
                review_state=ReviewState.PENDING.value,
            )
            db.add(sem_ev)
            extracted_events.append(sem_ev)

        if is_decision:
            sem_ev = SemanticEvent(
                id=str(uuid.uuid4()),
                meeting_id=meeting_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                event_type=SemanticEventType.DECISION_CANDIDATE.value,
                evidence_ids=[ev_id],
                confidence=0.89,
                extraction_stage="LIVE_PERCEPTION",
                review_state=ReviewState.PENDING.value,
            )
            db.add(sem_ev)
            extracted_events.append(sem_ev)

            # Create candidate decision
            dec = Decision(
                id=str(uuid.uuid4()),
                meeting_id=meeting_id,
                semantic_event_id=sem_ev.id,
                text=text,
                status=DecisionStatus.CANDIDATE,
                evidence_ids=[ev_id],
                confidence=0.89,
                review_state="PENDING",
            )
            db.add(dec)

        elif is_action:
            sem_ev = SemanticEvent(
                id=str(uuid.uuid4()),
                meeting_id=meeting_id,
                start_ms=start_ms,
                end_ms=end_ms,
                text=text,
                event_type=SemanticEventType.COMMITMENT.value,
                evidence_ids=[ev_id],
                confidence=0.85,
                extraction_stage="LIVE_PERCEPTION",
                review_state=ReviewState.PENDING.value,
            )
            db.add(sem_ev)
            extracted_events.append(sem_ev)

            act = ActionItem(
                id=str(uuid.uuid4()),
                originating_meeting_id=meeting_id,
                originating_timestamp_ms=start_ms,
                task=text,
                owner_id=None,
                owner_confidence=0.70,
                deadline=None,
                deadline_confidence=0.60,
                status=ActionItemStatus.PENDING,
                priority=ActionItemPriority.MEDIUM,
                evidence_ids=[ev_id],
                confidence=0.85,
                review_state="PENDING",
            )
            db.add(act)

        await db.commit()

        # 4. Trigger contradiction check if disagreement or decision was registered
        detected_contradictions = []
        if is_disagreement or is_decision:
            detected_contradictions = await contradiction_detector.detect_within_meeting(
                db=db, meeting_id=meeting_id
            )

        # 5. Broadcast live events over WebSocket
        ws_payload = {
            "type": "LIVE_UTTERANCE_PROCESSED",
            "segment": {
                "id": seg.id,
                "meeting_id": meeting_id,
                "text": text,
                "start_ms": start_ms,
                "end_ms": end_ms,
                "speaker_name": speaker_name or "Speaker",
                "asr_confidence": confidence,
            },
            "evidence_id": ev_id,
            "events_count": len(extracted_events),
            "contradictions_count": len(detected_contradictions),
        }
        await ws_manager.broadcast(meeting_id, ws_payload)

        return ws_payload


live_processor = LiveCaptureProcessor()
