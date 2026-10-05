"""
pipeline/asr/asr_adapter.py — Abstract ASR provider interface.

ALL ASR calls go through this interface.
Never import whisper or any ASR SDK outside of their adapter files.

See ADR-003 for rationale.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ASRSegment:
    """One utterance from ASR output."""
    start_ms: int
    end_ms: int
    text: str
    confidence: float
    language: str = "en"
    speaker_label: str | None = None  # populated by diarization stage, not ASR


@dataclass
class ASRResult:
    """Full ASR output for an audio file."""
    segments: list[ASRSegment] = field(default_factory=list)
    language: str = "en"
    duration_ms: int = 0
    model_used: str = ""
    adapter_used: str = ""


class ASRAdapter(ABC):
    """
    Abstract ASR provider interface.

    Implementations: WhisperLocalAdapter, WhisperAPIAdapter, StubASRAdapter
    Selected via ASR_PROVIDER env var in config.py.
    """

    @abstractmethod
    async def transcribe(
        self,
        audio_path: Path,
        language: str | None = None,
    ) -> ASRResult:
        """
        Transcribe an audio file.

        Args:
            audio_path: Absolute path to the audio file
            language: Optional language hint (e.g. "en", "hi")
        Returns:
            ASRResult with segments, each carrying confidence
        Raises:
            FileNotFoundError: if audio_path does not exist
            RuntimeError: if transcription fails
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if this adapter's dependencies are installed and configured."""


def get_asr_adapter() -> ASRAdapter:
    """Factory: return the configured ASR adapter."""
    from app.config import settings, ASRProvider

    if settings.asr_provider == ASRProvider.STUB:
        from app.pipeline.asr.stub_asr import StubASRAdapter
        return StubASRAdapter()
    elif settings.asr_provider == ASRProvider.WHISPER_LOCAL:
        from app.pipeline.asr.whisper_local import WhisperLocalAdapter
        return WhisperLocalAdapter()
    elif settings.asr_provider == ASRProvider.WHISPER_API:
        from app.pipeline.asr.whisper_api import WhisperAPIAdapter
        return WhisperAPIAdapter()
    else:
        raise ValueError(f"Unknown ASR provider: {settings.asr_provider}")
