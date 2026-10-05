# AI Meeting Intelligence System

**An evidence-grounded meeting intelligence operating system.**

> Not an AI transcription app. Not a summarizer. A structured, evidence-backed, human-correctable, organizationally-persistent meeting intelligence system.

---

## Quick Links

| Document | Purpose |
|---|---|
| [AGENTS.md](docs/AGENTS.md) | Agent instructions — how to operate in this codebase |
| [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | 12-layer architecture, module layout |
| [DATA_AND_PROVENANCE_MODEL.md](docs/DATA_AND_PROVENANCE_MODEL.md) | 22 entities, evidence model, provenance chain |
| [SYSTEM_STATE_MODEL.md](docs/SYSTEM_STATE_MODEL.md) | State machines, lifecycle, OODA loop |
| [CAPABILITIES.md](docs/CAPABILITIES.md) | Current capabilities by phase |
| [ROADMAP.md](docs/ROADMAP.md) | 8-phase implementation plan |
| [REPOSITORY_MAP.md](docs/REPOSITORY_MAP.md) | File-by-file directory map |
| [ADRs](docs/adr/) | Architecture Decision Records |

---

## What This System Does

```
INPUT AUDIO / VIDEO / NOTES / MANUAL MARKS
    ↓
EVIDENCE ACQUISITION (Capture Mode: RECORDING | OVERLAY | IMPORT | NOTES_ONLY)
    ↓
PERCEPTION (ASR + Diarization → TranscriptSegments)
    ↓
IDENTITY RESOLUTION (Speaker ↔ Participant)
    ↓
SEMANTIC EVENT EXTRACTION (Decisions, Actions, Questions, Contradictions)
    ↓
MEETING WORLD MODEL (structured, evidence-grounded)
    ↓
VALIDATION + CONFIDENCE SCORING
    ↓
CANONICAL MEETING RECORD (the authoritative structured state)
    ↓
HUMAN REVIEW (focused, ranked, minimal interruption)
    ↓
ARTIFACT GENERATION (DOCX, PDF, JSON, CSV)
    ↓
KNOWLEDGE ACCRETION (persistent organizational memory)
```

---

## Running Locally

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
cp .env.example .env            # edit with your keys
alembic upgrade head            # create DB schema
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # starts at http://localhost:5173
```

---

## Current Phase

**Phase 0 — Scaffold + Domain Model + Documentation**

See [CAPABILITIES.md](docs/CAPABILITIES.md) for what is currently operational.

---

## Architecture Invariants

1. Evidence is the ground truth. Generated prose is never authoritative.
2. MeetingRecord is the canonical aggregate. DOCX/PDF/UI are renderings.
3. Every extracted claim carries an evidence reference.
4. The Overlay Shell is independent of Capture Controllers.
5. Confidence is field-level, not meeting-level.
6. Human attention is a limited resource — review items are ranked.
7. Corrections create new Evidence records; never mutate existing ones.
8. Pipeline stages are idempotent; corrections invalidate only downstream stages.
9. Inferred knowledge is never silently promoted to verified knowledge.
10. Overlay Shell remains operational even if audio capture fails.

See [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) for the complete invariant list.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 19 + TypeScript + Vite |
| Backend | Python 3.14 + FastAPI |
| Real-time | WebSocket (FastAPI) |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.x + Alembic |
| ASR | Whisper (local) or API — provider abstraction |
| Diarization | pyannote.audio — provider abstraction |
| LLM | OpenAI / Anthropic / Ollama — provider abstraction |
| DOCX | python-docx |
| PDF | WeasyPrint → fallback reportlab |
| Desktop Overlay | pywebview |
| State (FE) | Zustand |
| Styling | Vanilla CSS (design tokens) |
