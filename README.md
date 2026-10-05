# MOM for meetings

**An evidence-grounded meeting intelligence operating system.**

> Not an AI transcription app. Not a summarizer. A structured, evidence-backed, human-correctable, organizationally-persistent meeting intelligence system.

---

## QUICK START

### Windows (One-Click Launch)
Double-click:
```
START_MOM.bat
```
or run in PowerShell:
```powershell
.\scripts\start.ps1
```
*The browser opens automatically at http://localhost:5173 once both FastAPI and Vite are responsive. Zero API keys, models, or cloud credentials required to explore.*

### Troubleshooting & Diagnostics
```powershell
.\scripts\doctor.ps1
```

### Clean Service Shutdown
Double-click:
```
STOP_MOM.bat
```
or run:
```powershell
.\scripts\stop.ps1
```

### Service Restart
```powershell
.\scripts\restart.ps1
```

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

**Phase 8 — External Integrations (Calendar Sync, Pre-Meeting Briefs, Task Export)**

Features implemented:
- Full 22 ORM entity models with async SQLite/PostgreSQL layer
- Progressive processing pipeline (ASR → Diarization → Identity → Semantic Extraction → Artifacts)
- Evidence provenance chain & Human Correction Engine (ADR-008, ADR-010, ADR-011)
- DOCX Artifact generation from canonical `MeetingRecord`
- Standalone Desktop Overlay Shell with always-on-top pywebview/browser launcher (`desktop/overlay_launcher.py`)
- Hardware-adaptive Capture Controllers (`MicCaptureController`, `SystemAudioController`, `ManualEventController`) with graceful degradation to `NO_AUDIO` mode
- Mark Moment engine (`Ctrl+Shift+M`) generating immutable `Evidence` (`source="HUMAN"`, `confidence=1.0`, `priority=1.0`)
- Real-time streaming utterance processor (`OVERLAY` mode) with automatic speech segment creation & real-time semantic event triggers
- Contradiction Detection Engine (`backend/app/pipeline/contradictions.py`) with strict invariant preferring `DECISION UNRESOLVED` over arbitrary resolution
- Cross-meeting continuity resolver (`backend/app/pipeline/continuity.py`): tracks `ActionItem` lifecycle across meetings, preserves `originating_meeting_id`, records `last_updated_meeting_id`, and appends immutable `CONTINUITY_UPDATE` evidence
- KnowledgeItem accretion pipeline (`backend/app/pipeline/knowledge_accretion.py`): accretes confirmed decisions, architectural patterns, and facts into persistent organizational memory with deduplication across `source_meeting_ids`
- Strict KnowledgeItem invariant: `verified=True` requires EITHER human verification (`source="HUMAN"`) OR system confidence >= 0.85; `INFERRED` alone is NEVER sufficient to set `verified=True`
- Terminology dictionary engine & UI: auto-detects technical terms & acronyms, tracks source meetings, supports human verification and custom term additions
- People Directory with cross-meeting intelligence (`/api/people/directory`): aggregated speaking times, open vs completed task counts, resolved speaker aliases, and complete meeting attendance history
- Knowledge Base UI (`frontend/src/pages/Knowledge.tsx`): 4-tab command center for Knowledge Base, Terminology Dictionary, Cross-Meeting Actions, and Decision Reversals
- Natural Language Query Engine (`backend/app/pipeline/query_engine.py`): classifies query intents (`ACTION_OWNER`, `DECISION_STATUS`, `CONTRADICTION`, `TIMELINE`, `FACTUAL`, `GENERAL`), performs multi-modal evidence retrieval across transcript segments, decisions, actions, user marks, and contradictions
- Strict Evidence Grounding Invariant: Every answer is strictly grounded in retrieved evidence; ungrounded questions return `grounded=False`, `confidence=0.0`, with explicit statement of missing evidence (zero hallucination)
- Structured `MeetingQueryAnswer` schema with rich `AnswerSource[]` citations
- Interactive "Ask the Meeting" UI in `MeetingWorkspace.tsx`: instant query bar, suggested question chips, grounded status badges, and clickable citation links to inspect evidence
- Bi-directional Calendar Synchronization: Google Calendar API v3 and Microsoft Graph / Outlook adapters with live & sandbox modes
- Pre-Meeting Intelligence Brief Generator (`backend/app/integrations/calendar/brief_generator.py`): analyzes attendees, titles, prior meeting history, and open action items to auto-generate canonical `MeetingBrief` entities
- Action Item Task Export Adapters: 1-click export to Atlassian Jira (`MOM-XXX`), GitHub Issues (`#XX`), and Linear (`MOM-XX`) with verbatim evidence citations and back-links
- Integrations Management UI (`frontend/src/pages/Integrations.tsx`): multi-provider configuration, connection test matrix, and upcoming calendar sync feed with 1-click "Import & Generate Brief" action
- In-Workspace Pre-Meeting Context banner and Action Items export toolbar with verified external issue links

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
