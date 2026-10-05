"""
config.py — Application settings via pydantic-settings.

All values are loaded from environment variables or .env file.
See .env.example for documentation of each setting.
"""
from enum import Enum
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProvider(str, Enum):
    STUB = "stub"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class ASRProvider(str, Enum):
    STUB = "stub"
    WHISPER_LOCAL = "whisper_local"
    WHISPER_API = "whisper_api"


class DiarizationProvider(str, Enum):
    STUB = "stub"
    PYANNOTE = "pyannote"


class PrivacyMode(str, Enum):
    LOCAL = "LOCAL"
    CLOUD = "CLOUD"
    HYBRID = "HYBRID"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_title: str = "MOM for meetings"
    app_version: str = "0.1.0"
    debug: bool = True

    # Database
    database_url: str = "sqlite+aiosqlite:///./meeting_intelligence.db"

    # LLM
    llm_provider: LLMProvider = LLMProvider.STUB
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # ASR
    asr_provider: ASRProvider = ASRProvider.STUB
    whisper_model: str = "base"

    # Diarization
    diarization_provider: DiarizationProvider = DiarizationProvider.STUB
    pyannote_auth_token: str = ""

    # Storage
    storage_root: Path = Path("./storage")

    # Privacy
    default_privacy_mode: PrivacyMode = PrivacyMode.LOCAL

    # Confidence thresholds
    min_auto_accept_confidence: float = 0.90
    min_review_surface_confidence: float = 0.60

    # Overlay
    overlay_port: int = 8001
    overlay_hotkey: str = "ctrl+shift+m"

    # CORS
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @property
    def audio_storage(self) -> Path:
        return self.storage_root / "audio"

    @property
    def artifact_storage(self) -> Path:
        return self.storage_root / "artifacts"

    @property
    def import_storage(self) -> Path:
        return self.storage_root / "imports"

    def ensure_storage_dirs(self) -> None:
        """Create storage directories if they don't exist."""
        for d in (self.audio_storage, self.artifact_storage, self.import_storage):
            d.mkdir(parents=True, exist_ok=True)


# Singleton settings instance
settings = Settings()
