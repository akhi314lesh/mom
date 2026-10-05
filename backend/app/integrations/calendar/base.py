"""backend/app/integrations/calendar/base.py — Abstract Calendar Adapter and models."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class CalendarEventAttendee(BaseModel):
    name: str
    email: str
    response_status: str = "accepted"  # accepted, tentative, declined, needsAction


class CalendarEvent(BaseModel):
    id: str
    provider: str  # "google" | "outlook"
    title: str
    description: str = ""
    start_time: datetime
    end_time: datetime
    attendees: List[CalendarEventAttendee] = Field(default_factory=list)
    location: Optional[str] = None
    meeting_link: Optional[str] = None
    status: str = "confirmed"  # confirmed, tentative, cancelled
    raw_event_data: dict = Field(default_factory=dict)


class BaseCalendarAdapter(ABC):
    """Abstract base class for calendar service providers."""

    @abstractmethod
    async def get_upcoming_events(
        self,
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
        limit: int = 10,
    ) -> List[CalendarEvent]:
        """Fetch upcoming calendar events for the authenticated account."""
        pass

    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[CalendarEvent]:
        """Fetch single event by ID."""
        pass

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test API credentials and return connectivity status."""
        pass
