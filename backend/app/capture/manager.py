"""
app/capture/manager.py — Capture session manager.

Coordinates audio capture controllers and the manual mark controller.
Updates CaptureSession and CaptureSource records in the database,
computes AudioSourceState and EvidenceManifest, and broadcasts real-time
telemetry to the desktop overlay and workspace via WebSocket.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import manager as ws_manager
from app.capture.controllers import (
    ManualEventController,
    MicrophoneCaptureController,
    SystemAudioCaptureController,
)
from app.models.capture import (
    AudioSourceState,
    CaptureSession,
    CaptureSource,
    CaptureSourceStatus,
    CaptureSourceType,
)
from app.models.meeting import Meeting, MeetingLifecycle

logger = logging.getLogger(__name__)


class CaptureSessionCoordinator:
    """Manages active capture controllers and state for meetings."""

    def __init__(self):
        # meeting_id -> dict of controllers
        self._active_controllers: Dict[str, Dict[str, Any]] = {}

    def get_controllers(self, meeting_id: str) -> Dict[str, Any]:
        if meeting_id not in self._active_controllers:
            self._active_controllers[meeting_id] = {
                "mic": MicrophoneCaptureController(),
                "sys": SystemAudioCaptureController(),
                "manual": ManualEventController(),
            }
        return self._active_controllers[meeting_id]

    def compute_audio_state(self, mic_active: bool, sys_active: bool) -> AudioSourceState:
        if mic_active and sys_active:
            return AudioSourceState.MICROPHONE_AND_SYS
        elif mic_active:
            return AudioSourceState.MICROPHONE_ONLY
        elif sys_active:
            return AudioSourceState.SYSTEM_ONLY
        else:
            return AudioSourceState.NO_AUDIO

    def build_evidence_manifest(self, mic_status: dict, sys_status: dict) -> dict:
        available = ["MANUAL_MARKS", "NOTES", "TIMESTAMPS"]
        unavailable = []
        reasons = []

        if mic_status.get("is_active"):
            available.append("MICROPHONE_AUDIO")
        else:
            unavailable.append("MICROPHONE_AUDIO")
            if mic_status.get("degradation_reason"):
                reasons.append(f"Mic: {mic_status['degradation_reason']}")

        if sys_status.get("is_active"):
            available.append("SYSTEM_AUDIO")
        else:
            unavailable.append("SYSTEM_AUDIO")
            if sys_status.get("degradation_reason"):
                reasons.append(f"System: {sys_status['degradation_reason']}")

        unavailable.append("VIDEO")  # Video is explicitly unsupported per architecture

        return {
            "available_sources": available,
            "unavailable_sources": unavailable,
            "degradation_reason": "; ".join(reasons) if reasons else None,
        }

    def build_audio_source_status(
        self, state: AudioSourceState, mic_status: dict, sys_status: dict, requested_mode: str
    ) -> dict:
        fallback_applied = state == AudioSourceState.NO_AUDIO and requested_mode != "NOTES_ONLY"
        reasons = []
        if mic_status.get("degradation_reason"):
            reasons.append(f"Mic: {mic_status['degradation_reason']}")
        if sys_status.get("degradation_reason"):
            reasons.append(f"System: {sys_status['degradation_reason']}")

        return {
            "state": state.value,
            "microphone_available": mic_status.get("status") in ("ACTIVE", "PAUSED"),
            "microphone_device": mic_status.get("device_name"),
            "system_audio_available": sys_status.get("status") in ("ACTIVE", "PAUSED"),
            "system_audio_device": sys_status.get("device_name"),
            "degradation_reason": "; ".join(reasons) if reasons else None,
            "fallback_applied": fallback_applied,
        }

    async def start_session(
        self,
        db: AsyncSession,
        meeting_id: str,
        capture_mode: str = "OVERLAY",
        enable_mic: bool = True,
        enable_sys: bool = True,
    ) -> CaptureSession:
        """Start or re-activate a CaptureSession with graceful degradation."""
        controllers = self.get_controllers(meeting_id)

        # Attempt starting mic
        mic_started = False
        if enable_mic:
            mic_started = await controllers["mic"].start()

        # Attempt starting system audio
        sys_started = False
        if enable_sys:
            sys_started = await controllers["sys"].start()

        # Manual is always active
        await controllers["manual"].start()

        mic_status = controllers["mic"].get_status()
        sys_status = controllers["sys"].get_status()

        audio_state = self.compute_audio_state(mic_started, sys_started)
        manifest = self.build_evidence_manifest(mic_status, sys_status)
        source_status = self.build_audio_source_status(audio_state, mic_status, sys_status, capture_mode)

        # Check existing active session
        stmt = select(CaptureSession).where(
            CaptureSession.meeting_id == meeting_id,
            CaptureSession.is_active == True,
        )
        result = await db.execute(stmt)
        session = result.scalars().first()

        now = datetime.now(timezone.utc)

        if not session:
            session = CaptureSession(
                meeting_id=meeting_id,
                capture_mode=capture_mode,
                audio_source_state=audio_state.value,
                audio_source_status=source_status,
                evidence_manifest=manifest,
                privacy_mode="LOCAL",
                is_active=True,
                started_at=now,
            )
            db.add(session)
            await db.flush()

            # Add child CaptureSource records
            mic_source = CaptureSource(
                capture_session_id=session.id,
                source_type=CaptureSourceType.MICROPHONE.value,
                status=mic_status["status"],
                device_name=mic_status.get("device_name"),
                degradation_reason=mic_status.get("degradation_reason"),
            )
            sys_source = CaptureSource(
                capture_session_id=session.id,
                source_type=CaptureSourceType.SYSTEM_AUDIO.value,
                status=sys_status["status"],
                device_name=sys_status.get("device_name"),
                degradation_reason=sys_status.get("degradation_reason"),
            )
            manual_source = CaptureSource(
                capture_session_id=session.id,
                source_type=CaptureSourceType.MANUAL.value,
                status=CaptureSourceStatus.ACTIVE.value,
                device_name="Keyboard & Desktop Overlay",
            )
            db.add_all([mic_source, sys_source, manual_source])
        else:
            session.audio_source_state = audio_state.value
            session.audio_source_status = source_status
            session.evidence_manifest = manifest

        # Update meeting lifecycle to CAPTURING
        meeting = await db.get(Meeting, meeting_id)
        if meeting:
            meeting.lifecycle_status = MeetingLifecycle.CAPTURING.value
            meeting.capture_mode = capture_mode

        await db.commit()
        await db.refresh(session)

        # Broadcast state to WebSocket
        await ws_manager.broadcast(
            meeting_id,
            {
                "type": "CAPTURE_SESSION_STARTED",
                "session_id": session.id,
                "audio_source_state": session.audio_source_state,
                "audio_source_status": session.audio_source_status,
                "evidence_manifest": session.evidence_manifest,
            },
        )

        return session

    async def stop_session(self, db: AsyncSession, meeting_id: str) -> Optional[CaptureSession]:
        """Stop active capture session."""
        controllers = self._active_controllers.get(meeting_id)
        if controllers:
            await controllers["mic"].stop()
            await controllers["sys"].stop()
            await controllers["manual"].stop()

        stmt = select(CaptureSession).where(
            CaptureSession.meeting_id == meeting_id,
            CaptureSession.is_active == True,
        )
        result = await db.execute(stmt)
        session = result.scalars().first()

        if session:
            session.is_active = False
            session.ended_at = datetime.now(timezone.utc)

            # Update meeting status to REVIEWING
            meeting = await db.get(Meeting, meeting_id)
            if meeting:
                meeting.lifecycle_status = MeetingLifecycle.REVIEWING.value

            await db.commit()
            await db.refresh(session)

            await ws_manager.broadcast(
                meeting_id,
                {
                    "type": "CAPTURE_SESSION_STOPPED",
                    "session_id": session.id,
                },
            )

        return session

    async def simulate_source_toggle(
        self,
        db: AsyncSession,
        meeting_id: str,
        source: str,
        force_fail: bool,
    ) -> Optional[CaptureSession]:
        """Allows testing graceful degradation by intentionally failing or restoring a source."""
        stmt = select(CaptureSession).where(
            CaptureSession.meeting_id == meeting_id,
            CaptureSession.is_active == True,
        )
        result = await db.execute(stmt)
        session = result.scalars().first()
        if not session:
            return None

        controllers = self.get_controllers(meeting_id)
        if source == "mic":
            if force_fail:
                controllers["mic"]._is_active = False
                controllers["mic"]._status = CaptureSourceStatus.FAILED
                controllers["mic"]._degradation_reason = "Simulated microphone hardware disconnect"
            else:
                controllers["mic"]._is_active = True
                controllers["mic"]._status = CaptureSourceStatus.ACTIVE
                controllers["mic"]._degradation_reason = None
        elif source == "sys":
            if force_fail:
                controllers["sys"]._is_active = False
                controllers["sys"]._status = CaptureSourceStatus.FAILED
                controllers["sys"]._degradation_reason = "Simulated WASAPI loopback failure"
            else:
                controllers["sys"]._is_active = True
                controllers["sys"]._status = CaptureSourceStatus.ACTIVE
                controllers["sys"]._degradation_reason = None

        mic_status = controllers["mic"].get_status()
        sys_status = controllers["sys"].get_status()
        audio_state = self.compute_audio_state(mic_status["is_active"], sys_status["is_active"])

        session.audio_source_state = audio_state.value
        session.evidence_manifest = self.build_evidence_manifest(mic_status, sys_status)
        session.audio_source_status = self.build_audio_source_status(
            audio_state, mic_status, sys_status, session.capture_mode
        )

        await db.commit()
        await db.refresh(session)

        await ws_manager.broadcast(
            meeting_id,
            {
                "type": "AUDIO_SOURCE_STATE_CHANGED",
                "audio_source_state": session.audio_source_state,
                "audio_source_status": session.audio_source_status,
                "evidence_manifest": session.evidence_manifest,
            },
        )
        return session


capture_manager = CaptureSessionCoordinator()
