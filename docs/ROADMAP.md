# ROADMAP.md

> **Version**: 1.0  
> **Last updated**: 2026-10-04

---

## Implementation Phases

### Phase 0 — Scaffold + Domain Model + Documentation
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-0): scaffold, domain model, documentation`

Deliverables:
- [x] `.gitignore`, `README.md`
- [x] All 10 architecture documentation files
- [x] All 10+ ADRs
- [x] Backend: FastAPI app, config, SQLAlchemy + Alembic setup
- [x] All 22 ORM models
- [x] All Pydantic v2 schemas
- [x] All adapter interfaces (abstract base classes)
- [x] All stub adapter implementations
- [x] Frontend: Vite React-TS scaffold
- [x] Frontend: Design system (CSS tokens, typography)
- [x] Frontend: All page shells with mock data
- [x] Frontend: Component shells

**Validation**: Both servers start. All pages render with mock data. DB schema created.

---

### Phase 1 — Core Pipeline + UI
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-1): core pipeline, transcript, semantic extraction, artifacts`

Deliverables:
- File upload endpoint + ingestion service
- ASR pipeline (WhisperLocal + Stub)
- Normalizer producing `TranscriptSegment[]`
- LLM semantic extraction (OpenAI + Stub)
- Decision / Action / Question extractors
- `MeetingRecord` builder
- DOCX generator (python-docx)
- PDF generator (WeasyPrint)
- Meeting Workspace UI (transcript, decisions, actions, quality metrics)
- Dashboard with recent meetings
- WebSocket progress updates during processing

**Validation**: Upload audio → processing → view transcript → view decisions → download DOCX → download PDF.

---

### Phase 2 — Evidence + Provenance + Review Queue
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-2): evidence provenance, field confidence, review queue`

Deliverables:
- Evidence links on all decisions/actions in UI
- Evidence panel (clickable; shows source, quote, confidence)
- Field-level confidence display everywhere
- Review queue backend (priority scoring)
- Review queue UI (focused, ranked items)
- Human correction flow (speaker, deadline, owner)
- Corrections persisted; artifacts marked STALE → regenerated
- Dependency-aware invalidation (only downstream stages)

**Validation**: Click decision → see evidence. Review queue shows ambiguous items. Resolve → re-download updated artifact. ASR stage NOT rerun.

---

### Phase 3 — Speaker Diarization + Participant Resolution
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-3): diarization, speaker resolution, participant mapping`

Deliverables:
- Diarization adapter (pyannote.audio + Stub)
- Speaker resolution (label → participant mapping)
- Participant management UI (People page)
- Speaker review items in queue

**Validation**: Multi-speaker audio → diarization → transcript shows speaker names with confidence.

---

### Phase 4 — Desktop Overlay + Mark Moment
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-4): overlay shell, capture controllers, mark moment`

Deliverables:
- Overlay shell (pywebview always-on-top)
- Capture controllers (mic, system audio WASAPI)
- `AudioSourceState` updated live
- Mark Moment (Ctrl+Shift+M → `UserMark` created)
- Manual event buttons (Note, Decision, Action, Flag)
- WebSocket sync overlay ↔ backend
- Overlay collapse/expand
- Graceful degradation: mic fail → manual mode, overlay stays active

**Validation**: Overlay opens → Ctrl+Shift+M → UserMark appears in workspace timeline. Unplug mic → overlay remains usable.

---

### Phase 5 — Live Capture + Semantic Timeline + Contradiction Detection
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-5): live capture, semantic timeline, contradiction detection`

Deliverables:
- OVERLAY capture mode (live processing pipeline)
- Semantic event timeline component
- Contradiction detector (within-meeting)
- Disagreement flag in UI
- Timeline events linked to evidence (click → jump)
- Cross-meeting action item continuity (basic)

**Validation**: Live meeting → timeline updates in real time → contradiction detected → flagged in UI → click → evidence shown.

---

### Phase 6 — Meeting Continuity + Memory + Terminology
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-6): continuity, cross-meeting memory, terminology`

Deliverables:
- Continuity resolver (ActionItem tracking across meetings)
- Cross-meeting contradiction detection
- KnowledgeItem accretion pipeline
- Terminology dictionary UI
- People page (full participant history)
- Knowledge page (searchable organizational memory)

**Validation**: Meeting 2 mentions M1 action item → status updated → cross-meeting link visible in both meetings.

---

### Phase 7 — Ask the Meeting
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-7): ask-the-meeting natural language queries`

Deliverables:
- Query endpoint (`POST /api/query`)
- Query classifier + evidence retrieval
- LLM synthesis with evidence grounding
- `MeetingQueryAnswer` with `AnswerSource[]`
- Query UI in Meeting Workspace sidebar

**Validation**: "Who agreed to handle authentication?" → answer with evidence link + quoted segment.

---

### Phase 8 — External Integrations
**Status**: ✅ Complete  
**Commit tag**: `feat(phase-8): calendar, task integrations`

Deliverables:
- Calendar adapter interface + implementations (Google Calendar, Outlook)
- Meeting brief auto-generation from calendar
- Task export adapters (Jira, GitHub Issues, Linear)
- Integration settings UI page
- In-workspace task export & pre-meeting intelligence brief view

---

## Architectural Rule

**No phase may weaken the abstractions of earlier phases.**

If a later phase requirement cannot be met without modifying a foundational abstraction, create an ADR documenting the deviation before changing anything.
