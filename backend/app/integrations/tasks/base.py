"""backend/app/integrations/tasks/base.py — Abstract Task Export Adapter and schemas."""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

from app.models.actions import ActionItem
from app.models.meeting import Meeting


class TaskExportRequest(BaseModel):
    action_item_id: str
    destination: Literal["jira", "github", "linear"]
    project_or_repo: Optional[str] = None  # e.g., "MOM", "owner/repo", "ENG"
    assignee_override: Optional[str] = None
    labels: list[str] = Field(default_factory=list)


class TaskExportReceipt(BaseModel):
    export_id: str
    action_item_id: str
    destination: str
    external_id: str  # e.g., "MOM-104", "#42", "LIN-55"
    external_url: str
    exported_at: datetime
    status: str = "success"
    task_summary: str
    evidence_quote_included: bool
    details: Dict[str, Any] = Field(default_factory=dict)


class BaseTaskExportAdapter(ABC):
    """Abstract base class for exporting action items to external issue trackers."""

    @abstractmethod
    async def export_action_item(
        self,
        action: ActionItem,
        meeting: Meeting,
        evidence_quote: Optional[str] = None,
        owner_name: Optional[str] = None,
        options: Optional[dict] = None,
    ) -> TaskExportReceipt:
        """Export action item to the destination issue tracker."""
        pass

    @abstractmethod
    async def test_connection(self) -> dict:
        """Test API connection with the issue tracking platform."""
        pass
