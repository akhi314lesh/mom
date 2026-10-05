# OPERATIONS.md

> **Version**: 1.0  
> **Last updated**: 2026-10-04

---

## Prerequisites

- Python 3.11+ (tested on 3.14.7)
- Node.js 18+ (tested on 24.19.0)
- npm 9+ (tested on 11.17.0)
- Git

**For ML features (Phase 3+):**
- CUDA-capable GPU recommended for Whisper + pyannote
- Or CPU-only with longer processing times

---

## Development Setup

### 1. Backend

```powershell
cd backend

# Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys and preferences

# Create database schema
alembic upgrade head

# Run dev server
uvicorn app.main:app --reload --port 8000
```

Backend available at: `http://localhost:8000`  
API docs: `http://localhost:8000/docs`  
WebSocket: `ws://localhost:8000/ws/`

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend available at: `http://localhost:5173`

---

## Environment Variables (.env)

```
# Database
DATABASE_URL=sqlite:///./meeting_intelligence.db
# For PostgreSQL: DATABASE_URL=postgresql+asyncpg://user:pass@localhost/mom

# LLM Provider
LLM_PROVIDER=stub  # stub | openai | anthropic | ollama
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# ASR Provider
ASR_PROVIDER=stub  # stub | whisper_local | whisper_api
OPENAI_WHISPER_API_KEY=  # if using whisper_api

# Diarization Provider
DIARIZATION_PROVIDER=stub  # stub | pyannote
PYANNOTE_AUTH_TOKEN=  # huggingface token for pyannote

# Storage
STORAGE_ROOT=./storage
MAX_AUDIO_SIZE_MB=500

# Privacy
DEFAULT_PRIVACY_MODE=LOCAL  # LOCAL | CLOUD | HYBRID

# Confidence thresholds
MIN_AUTO_ACCEPT_CONFIDENCE=0.90
MIN_SURFACE_CONFIDENCE=0.60

# Overlay (Phase 4)
OVERLAY_PORT=8001
OVERLAY_HOTKEY=ctrl+shift+m
```

---

## Running Without API Keys

Set `LLM_PROVIDER=stub` and `ASR_PROVIDER=stub` in `.env`.

The stub adapters return realistic mock data. The entire UI, pipeline, and artifact generation work without any API keys or ML packages installed.

This is the default state for Phase 0.

---

## Running with Whisper (Phase 1+)

```powershell
# Install ML packages (heavy - requires torch)
pip install -r requirements-ml.txt

# Update .env
# ASR_PROVIDER=whisper_local
```

Note: `torch` installs ~2GB. On CPU-only machines, transcription will be slow. Consider using `ASR_PROVIDER=whisper_api` for faster processing via OpenAI's Whisper API.

---

## Database

**Development (default):** SQLite at `./backend/meeting_intelligence.db`

**Production:** Set `DATABASE_URL` to a PostgreSQL connection string.

```powershell
# Create/update schema
alembic upgrade head

# Create a new migration after model changes
alembic revision --autogenerate -m "description"

# Downgrade (careful in production)
alembic downgrade -1
```

---

## Storage

Generated files are stored under `backend/storage/`:

```
storage/
├── audio/        Uploaded/recorded audio files
├── artifacts/    Generated DOCX, PDF, JSON files
└── imports/      Imported transcript/document files
```

These directories are gitignored. On first run, Alembic upgrade creates `.gitkeep` files.

**OneDrive warning:** If the project is in an OneDrive-synced folder (as in the default setup), SQLite WAL mode can conflict with OneDrive sync. Recommendation: move the database file outside OneDrive for production use.

---

## Commit Convention

```
feat(phase-N): short description
fix(phase-N): short description
docs: short description
refactor: short description
test: short description
```

Examples:
```
feat(phase-0): add all 22 ORM models
feat(phase-1): implement WhisperLocalAdapter
fix(phase-1): handle empty transcript segments
docs: update CAPABILITIES.md for Phase 1
```
