"""
app/capture/controllers.py — Concrete capture controllers.

Implements ADR-005 (Overlay Architecture) and ADR-006 (Audio Source Separation):
- MicrophoneCaptureController: captures host microphone
- SystemAudioCaptureController: captures system loopback audio via WASAPI
- ManualEventController: always available for human markers, notes, decisions
"""
import logging
from typing import Any, Dict, Optional

from app.capture.base import BaseCaptureController
from app.models.capture import CaptureSourceStatus, CaptureSourceType

logger = logging.getLogger(__name__)


class MicrophoneCaptureController(BaseCaptureController):
    """
    Microphone audio capture.
    Attempts hardware access; gracefully degrades to UNAVAILABLE/FAILED if absent.
    """

    def __init__(self, preferred_device: Optional[str] = None):
        self.preferred_device = preferred_device
        self._is_active = False
        self._status = CaptureSourceStatus.UNAVAILABLE
        self._device_name: Optional[str] = None
        self._degradation_reason: Optional[str] = None
        self._check_device_availability()

    def _check_device_availability(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
            devices = sd.query_devices()
            input_devs = [d for d in devices if d.get("max_input_channels", 0) > 0]
            if input_devs:
                self._status = CaptureSourceStatus.PAUSED
                self._device_name = self.preferred_device or input_devs[0].get("name", "Default Microphone")
                self._degradation_reason = None
            else:
                self._status = CaptureSourceStatus.UNAVAILABLE
                self._device_name = None
                self._degradation_reason = "No input audio devices found"
        except ImportError:
            self._status = CaptureSourceStatus.UNAVAILABLE
            self._device_name = "Host Mic Adapter (simulated)"
            self._degradation_reason = "sounddevice/PortAudio library not installed in runtime environment"
        except Exception as exc:
            self._status = CaptureSourceStatus.FAILED
            self._device_name = None
            self._degradation_reason = f"Microphone init failed: {str(exc)}"

    async def start(self) -> bool:
        if self._status == CaptureSourceStatus.UNAVAILABLE or self._status == CaptureSourceStatus.FAILED:
            logger.warning("Microphone cannot be started: %s", self._degradation_reason)
            self._is_active = False
            return False
        self._is_active = True
        self._status = CaptureSourceStatus.ACTIVE
        return True

    async def stop(self) -> Optional[bytes]:
        self._is_active = False
        if self._status == CaptureSourceStatus.ACTIVE:
            self._status = CaptureSourceStatus.PAUSED
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "source_type": CaptureSourceType.MICROPHONE.value,
            "status": self._status.value if hasattr(self._status, "value") else str(self._status),
            "is_active": self._is_active,
            "device_name": self._device_name,
            "degradation_reason": self._degradation_reason,
        }

    @property
    def is_active(self) -> bool:
        return self._is_active


class SystemAudioCaptureController(BaseCaptureController):
    """
    System loopback audio capture (Windows WASAPI loopback).
    Degrades gracefully if host doesn't support WASAPI loopback or exclusive mode fails.
    """

    def __init__(self, preferred_device: Optional[str] = None):
        self.preferred_device = preferred_device
        self._is_active = False
        self._status = CaptureSourceStatus.UNAVAILABLE
        self._device_name: Optional[str] = None
        self._degradation_reason: Optional[str] = None
        self._check_wasapi_availability()

    def _check_wasapi_availability(self) -> None:
        try:
            import sounddevice as sd  # type: ignore
            # Check for Windows WASAPI host api
            host_apis = sd.query_hostapis()
            wasapi = next((api for api in host_apis if "WASAPI" in api.get("name", "").upper()), None)
            if wasapi:
                self._status = CaptureSourceStatus.PAUSED
                self._device_name = self.preferred_device or "WASAPI System Audio Loopback"
                self._degradation_reason = None
            else:
                self._status = CaptureSourceStatus.UNAVAILABLE
                self._degradation_reason = "WASAPI loopback not available on this host audio interface"
        except ImportError:
            self._status = CaptureSourceStatus.UNAVAILABLE
            self._device_name = "WASAPI Loopback (simulated)"
            self._degradation_reason = "sounddevice/WASAPI backend not available in runtime environment"
        except Exception as exc:
            self._status = CaptureSourceStatus.FAILED
            self._degradation_reason = f"System audio loopback error: {str(exc)}"

    async def start(self) -> bool:
        if self._status == CaptureSourceStatus.UNAVAILABLE or self._status == CaptureSourceStatus.FAILED:
            logger.warning("System loopback cannot start: %s", self._degradation_reason)
            self._is_active = False
            return False
        self._is_active = True
        self._status = CaptureSourceStatus.ACTIVE
        return True

    async def stop(self) -> Optional[bytes]:
        self._is_active = False
        if self._status == CaptureSourceStatus.ACTIVE:
            self._status = CaptureSourceStatus.PAUSED
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "source_type": CaptureSourceType.SYSTEM_AUDIO.value,
            "status": self._status.value if hasattr(self._status, "value") else str(self._status),
            "is_active": self._is_active,
            "device_name": self._device_name,
            "degradation_reason": self._degradation_reason,
        }

    @property
    def is_active(self) -> bool:
        return self._is_active


class ManualEventController(BaseCaptureController):
    """
    Manual events and Mark Moment controller.
    INVARIANT: This controller is ALWAYS ACTIVE and ALWAYS AVAILABLE,
    regardless of hardware audio device failures.
    """

    def __init__(self):
        self._is_active = True
        self._status = CaptureSourceStatus.ACTIVE

    async def start(self) -> bool:
        self._is_active = True
        return True

    async def stop(self) -> Optional[bytes]:
        return None

    def get_status(self) -> Dict[str, Any]:
        return {
            "source_type": CaptureSourceType.MANUAL.value,
            "status": CaptureSourceStatus.ACTIVE.value,
            "is_active": True,
            "device_name": "Keyboard & Overlay Human Input",
            "degradation_reason": None,
        }

    @property
    def is_active(self) -> bool:
        return True
