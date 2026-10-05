"""backend/app/integrations/calendar/brief_generator.py — Meeting Brief Auto-Generation."""
import re
import uuid
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.meeting import Meeting
from app.models.brief import MeetingBrief
from app.models.participant import Participant
from app.models.actions import ActionItem, ActionItemStatus
from app.models.questions import Question
from app.integrations.calendar.base import CalendarEvent


class MeetingBriefGenerator:
    """
    Analyzes upcoming meetings, attendees, prior meeting history, and open action items
    to generate an evidence-grounded pre-meeting MeetingBrief entity.
    """

    async def generate_brief_for_meeting(
        self,
        db: AsyncSession,
        meeting_id: str,
        calendar_event: Optional[CalendarEvent] = None,
    ) -> MeetingBrief:
        # 1. Fetch meeting
        stmt = select(Meeting).where(Meeting.id == meeting_id)
        res = await db.execute(stmt)
        meeting = res.scalar_one_or_none()
        if not meeting:
            raise ValueError(f"Meeting {meeting_id} not found")

        # 2. Collect participant names/emails
        p_stmt = select(Participant).where(Participant.meeting_id == meeting_id)
        p_res = await db.execute(p_stmt)
        participants = list(p_res.scalars().all())
        participant_names = {p.name.lower() for p in participants}

        if calendar_event:
            for att in calendar_event.attendees:
                participant_names.add(att.name.lower())

        # 3. Find relevant previous meetings (matching attendees or keyword overlap)
        prev_m_stmt = select(Meeting).where(Meeting.id != meeting_id)
        prev_m_res = await db.execute(prev_m_stmt)
        all_prev_meetings = list(prev_m_res.scalars().all())

        title_tokens = set(re.findall(r"\w+", meeting.title.lower())) - {
            "meeting", "sync", "review", "sprint", "and", "the", "for", "in", "to", "of", "a", "with"
        }

        # Fetch participants of all previous meetings to score attendee overlap
        all_p_stmt = select(Participant)
        all_p_res = await db.execute(all_p_stmt)
        m_to_attendees = {}
        for p in all_p_res.scalars().all():
            m_to_attendees.setdefault(p.meeting_id, set()).add(p.name.lower())

        scored_meetings = []
        for pm in all_prev_meetings:
            pm_tokens = set(re.findall(r"\w+", pm.title.lower())) - {
                "meeting", "sync", "review", "sprint", "and", "the", "for", "in", "to", "of", "a", "with"
            }
            overlap_words = title_tokens.intersection(pm_tokens)
            score = len(overlap_words) * 10

            pm_attendees = m_to_attendees.get(pm.id, set())
            att_overlap = participant_names.intersection(pm_attendees)
            score += len(att_overlap) * 5

            scored_meetings.append((pm, score))

        # Sort by score descending, then date descending
        scored_meetings.sort(key=lambda item: (item[1], item[0].date), reverse=True)
        previous_meeting_ids: List[str] = [item[0].id for item in scored_meetings[:5]]

        # 4. Find open action items (assigned to attendees or from prior meetings)
        act_stmt = select(ActionItem).where(
            ActionItem.status.in_([ActionItemStatus.PENDING, ActionItemStatus.IN_PROGRESS])
        )
        act_res = await db.execute(act_stmt)
        all_open_actions = list(act_res.scalars().all())

        scored_actions = []
        for act in all_open_actions:
            act_score = 0
            if act.originating_meeting_id in previous_meeting_ids:
                act_score += 20
            # Check if task keywords match current meeting topics
            act_tokens = set(re.findall(r"\w+", act.task.lower()))
            if title_tokens.intersection(act_tokens):
                act_score += 10
            scored_actions.append((act, act_score))

        scored_actions.sort(key=lambda item: item[1], reverse=True)
        open_action_item_ids: List[str] = [item[0].id for item in scored_actions[:8]]

        # 5. Find unresolved questions from prior meetings
        unresolved_question_ids: List[str] = []
        if previous_meeting_ids:
            q_stmt = select(Question).where(
                Question.meeting_id.in_(previous_meeting_ids),
                Question.answered == False,  # noqa: E712
            )
            q_res = await db.execute(q_stmt)
            unresolved_question_ids = [q.id for q in q_res.scalars().all()]

        # 6. Extract expected topics
        expected_topics: List[str] = []
        raw_text_corpus = f"{meeting.title} {meeting.description or ''}"
        if calendar_event:
            raw_text_corpus += f" {calendar_event.description}"

        # Topic heuristics
        topic_candidates = [
            "Architecture & System Design",
            "Authentication & OAuth Security",
            "Database & Storage Migrations",
            "Micro-animations & UI Polish",
            "Cross-Meeting Action Items",
            "Conflict Resolution & Disagreements",
            "API Rate Limiting & Performance",
        ]
        lower_corpus = raw_text_corpus.lower()
        for cand in topic_candidates:
            cand_words = set(re.findall(r"\w+", cand.lower())) - {"and", "&"}
            if any(w in lower_corpus for w in cand_words):
                expected_topics.append(cand)

        if not expected_topics:
            expected_topics = ["General Agenda & Status Updates", "Team Discussion & Action Items"]

        # 7. Collect relevant documents / links
        relevant_documents: List[str] = []
        if calendar_event and calendar_event.meeting_link:
            relevant_documents.append(f"Meeting Call: {calendar_event.meeting_link}")
        if calendar_event and calendar_event.location:
            relevant_documents.append(f"Location: {calendar_event.location}")

        # Search for URLs in description
        urls = re.findall(r"https?://[^\s]+", raw_text_corpus)
        for u in urls:
            if u not in relevant_documents and not any(u in rd for rd in relevant_documents):
                relevant_documents.append(u)

        # 8. Create or update MeetingBrief
        brief_stmt = select(MeetingBrief).where(MeetingBrief.meeting_id == meeting_id)
        b_res = await db.execute(brief_stmt)
        existing_brief = b_res.scalar_one_or_none()

        if existing_brief:
            existing_brief.title = f"Pre-Meeting Brief: {meeting.title}"
            existing_brief.previous_meeting_ids = previous_meeting_ids
            existing_brief.open_action_item_ids = open_action_item_ids
            existing_brief.expected_topics = expected_topics
            existing_brief.relevant_documents = relevant_documents
            existing_brief.unresolved_question_ids = unresolved_question_ids
            brief = existing_brief
        else:
            brief = MeetingBrief(
                id=str(uuid.uuid4()),
                meeting_id=meeting_id,
                title=f"Pre-Meeting Brief: {meeting.title}",
                previous_meeting_ids=previous_meeting_ids,
                open_action_item_ids=open_action_item_ids,
                expected_topics=expected_topics,
                relevant_documents=relevant_documents,
                unresolved_question_ids=unresolved_question_ids,
            )
            db.add(brief)

        # Update meeting briefing reference
        meeting.briefing_id = brief.id
        await db.commit()
        await db.refresh(brief)
        return brief


brief_generator = MeetingBriefGenerator()
