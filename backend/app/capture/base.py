"""
app/capture/base.py — Abstract base class for capture source controllers.

Enforces ADR-005 and ADR-006:
- Capture controllers operate independently.
- Failure of an individual audio source degrades gracefully without crashing the session.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseCaptureController(ABC):
    """Abstract interface for all hardware/software capture controllers."""

    @abstractmethod
    async def start(self) -> bool:
        """Start capturing from this source. Returns True if successfully activated."""
        ...

    @abstractmethod
    async def stop(self) -> Optional[bytes]:
        """Stop capture and return any accumulated audio/data buffer."""
        ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return current status dictionary (status, device_name, degradation_reason)."""
        ...

    @property
    @abstractmethod
    def is_active(self) -> bool:
        """True if actively capturing."""
        ...
