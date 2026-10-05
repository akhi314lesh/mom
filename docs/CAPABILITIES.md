# CAPABILITIES.md

> **Version**: 1.0 (Phase 0)  
> **Last updated**: 2026-10-04  
> **Current Phase**: 0 — Scaffold

---

## Currently Operational (Phase 0)

| Capability | Status | Notes |
|---|---|---|
| Repository structure | ✅ Complete | Backend + frontend + docs |
| Domain model (22 entities) | ✅ Defined | DB schema not yet created |
| Architecture documentation | ✅ Complete | All 10 docs + 10 ADRs |
| Provider adapter interfaces | ✅ Defined | ASR, Diarization, LLM |
| Stub adapters | ✅ Defined | Enables dev without ML stack |
| Frontend page shells | ✅ Scaffold | No real data yet |
| Backend API endpoints | 🔲 Skeleton | Handlers not yet implemented |
| DB schema migration | 🔲 Pending | Alembic setup Phase 1 |

---

## Phase 1 (Core Pipeline) — Target Capabilities

| Capability | Target |
|---|---|
| Audio file upload | Via API endpoint |
| ASR transcription | Whisper local + Stub |
| TranscriptSegment creation | Normalizer stage |
| Semantic extraction | LLM + extractors |
| Decision detection | DecisionExtractor |
| Action item extraction | ActionExtractor |
| Question extraction | QuestionExtractor |
| MeetingRecord assembly | WorldModelBuilder |
| DOCX generation | python-docx |
| PDF generation | WeasyPrint |
| Meeting Workspace UI | Full transcript + decisions + actions |
| WebSocket progress updates | Processing status |
| Evidence references | On decisions/actions |
| Quality metrics | Field-level confidence display |

---

## Phase 2 — Evidence + Review

| Capability | Target |
|---|---|
| Evidence panel (clickable) | Source, quote, confidence |
| Review queue (backend) | Priority-ranked items |
| Review queue (UI) | Focused correction flow |
| Human corrections | Speaker, deadline, owner |
| Artifact staleness | STALE → regenerate on correction |
| Dependency-aware invalidation | Only downstream stages |

---

## Phase 3 — Speaker Diarization

| Capability | Target |
|---|---|
| Speaker diarization | pyannote.audio |
| Speaker → Participant resolution | Identity resolver |
| Participant management UI | People page |
| Speaker review items | In review queue |

---

## Phase 4 — Desktop Overlay

| Capability | Target |
|---|---|
| Overlay shell | pywebview always-on-top |
| Microphone capture | sounddevice |
| System audio (WASAPI) | sounddevice WASAPI mode |
| Audio source state display | Live indicator |
| Mark Moment (Ctrl+Shift+M) | UserMark creation |
| Manual events | Note, Decision, Action, Flag |
| WebSocket sync | Overlay ↔ backend |
| Graceful degradation | Mic fail → manual mode |

---

## Phase 5 — Timeline + Contradiction Detection

| Capability | Target |
|---|---|
| Semantic event timeline | Visual UI component |
| OVERLAY capture mode | Live processing |
| Contradiction detection | Within-meeting |
| Disagreement flagging | In UI |
| Timeline ↔ evidence links | Clickable jump |

---

## Phase 6 — Memory + Continuity

| Capability | Target |
|---|---|
| ActionItem continuity | Cross-meeting tracking |
| Cross-meeting contradictions | Detection + surfacing |
| KnowledgeItem accretion | Persistent facts |
| Terminology dictionary | Term → meaning |
| People page (full) | Participant history |
| Knowledge page (full) | Searchable memory |

---

## Phase 7 — Ask the Meeting

| Capability | Target |
|---|---|
| NL query endpoint | /api/query |
| Evidence-grounded answers | AnswerSource + quotes |
| Query UI | In Meeting Workspace |

---

## Phase 8 — External Integrations

| Capability | Target |
|---|---|
| Calendar integration | Google Calendar, Outlook |
| Meeting brief from calendar | Pre-meeting context |
| Task export | Jira, GitHub, Linear |
| Integration settings | Configurable adapters |

---

## Known Limitations (Phase 0)

- No audio processing — all ML features are stubs
- No real DB — schema not yet migrated
- No real API — handlers return mock data
- No real artifacts — generators are stubs
- No overlay — pywebview not yet implemented
- No live capture — planned Phase 4

---

## Not Planned (MVP Exclusions)

These are explicitly out of scope until after Phase 5:
- Video processing
- Meeting room hardware integration
- Speech synthesis / TTS
- Real-time multi-user collaboration
- Mobile app
