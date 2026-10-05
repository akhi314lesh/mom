# REPOSITORY_MAP.md

> **Version**: 1.0 (Phase 0)  
> **Last updated**: 2026-10-04

---

```
mom/
├── .gitignore
├── README.md
│
├── docs/                                    Architecture documentation
│   ├── AGENTS.md                            ← READ FIRST (agent instructions)
│   ├── SYSTEM_ARCHITECTURE.md              ← 12-layer architecture
│   ├── SYSTEM_STATE_MODEL.md               ← State machines, OODA loop
│   ├── CAPABILITIES.md                     ← Current + future capabilities
│   ├── DATA_AND_PROVENANCE_MODEL.md        ← 22 entities, provenance
│   ├── OPERATIONS.md                       ← How to run the system
│   ├── RESOURCE_AWARE_EXECUTION.md         ← Progressive processing
│   ├── QUALITY_AND_VALIDATION.md           ← Confidence, quality metrics
│   ├── ROADMAP.md                          ← 8-phase plan
│   ├── REPOSITORY_MAP.md                   ← This file
│   └── adr/                                Architecture Decision Records
│       ├── ADR-001-database-strategy.md
│       ├── ADR-002-llm-provider-abstraction.md
│       ├── ADR-003-asr-provider-abstraction.md
│       ├── ADR-004-capture-mode-abstraction.md
│       ├── ADR-005-overlay-architecture.md
│       ├── ADR-006-audio-source-separation.md
│       ├── ADR-007-canonical-meeting-record.md
│       ├── ADR-008-evidence-provenance-model.md
│       ├── ADR-009-confidence-model.md
│       ├── ADR-010-progressive-processing.md
│       └── ADR-011-artifact-invalidation.md
│
├── backend/
│   ├── requirements.txt                    Python dependencies
│   ├── requirements-dev.txt                Dev-only dependencies
│   ├── .env.example                        Environment variable template
│   ├── alembic.ini                         Alembic configuration
│   │
│   ├── alembic/                            DB migrations
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/                       Migration files
│   │
│   ├── app/
│   │   ├── main.py                         FastAPI app entry point
│   │   ├── config.py                       pydantic-settings configuration
│   │   ├── database.py                     SQLAlchemy engine + session
│   │   │
│   │   ├── models/                         SQLAlchemy ORM models (Layer 1 persistence)
│   │   │   ├── __init__.py
│   │   │   ├── meeting.py                  Meeting, MeetingSession
│   │   │   ├── capture.py                  CaptureSession, CaptureSource
│   │   │   ├── participant.py              Participant, Speaker
│   │   │   ├── transcript.py               TranscriptSegment
│   │   │   ├── evidence.py                 Evidence (immutable)
│   │   │   ├── semantic.py                 SemanticEvent, MeetingTopic
│   │   │   ├── decisions.py                Decision
│   │   │   ├── actions.py                  ActionItem (cross-meeting)
│   │   │   ├── questions.py                Question
│   │   │   ├── contradictions.py           Contradiction
│   │   │   ├── knowledge.py                KnowledgeItem, TerminologyEntry
│   │   │   ├── review.py                   ReviewItem
│   │   │   ├── processing.py               ProcessingRun, ProcessingLedger
│   │   │   ├── artifacts.py                Artifact
│   │   │   ├── brief.py                    MeetingBrief
│   │   │   └── marks.py                    UserMark
│   │   │
│   │   ├── schemas/                        Pydantic v2 schemas (API contracts)
│   │   │   ├── __init__.py
│   │   │   ├── meeting.py
│   │   │   ├── capture.py
│   │   │   ├── transcript.py
│   │   │   ├── evidence.py
│   │   │   ├── semantic.py
│   │   │   ├── decisions.py
│   │   │   ├── actions.py
│   │   │   ├── review.py
│   │   │   ├── knowledge.py
│   │   │   ├── processing.py
│   │   │   ├── artifacts.py
│   │   │   └── meeting_record.py           MeetingRecord aggregate + quality metrics
│   │   │
│   │   ├── api/                            FastAPI routers
│   │   │   ├── __init__.py
│   │   │   ├── meetings.py                 CRUD + lifecycle management
│   │   │   ├── capture.py                  Capture session management
│   │   │   ├── ingestion.py                File upload endpoint
│   │   │   ├── processing.py               Pipeline trigger + status
│   │   │   ├── transcript.py               Transcript view + edit
│   │   │   ├── evidence.py                 Evidence retrieval
│   │   │   ├── review.py                   Review queue management
│   │   │   ├── actions.py                  ActionItem CRUD
│   │   │   ├── decisions.py                Decision CRUD
│   │   │   ├── knowledge.py                Knowledge + terminology
│   │   │   ├── artifacts.py                DOCX/PDF download
│   │   │   ├── query.py                    Ask the Meeting
│   │   │   ├── agent_console.py            Agent state endpoint
│   │   │   └── ws.py                       WebSocket hub
│   │   │
│   │   ├── services/                       Business logic (no HTTP dependencies)
│   │   │   ├── meeting_service.py
│   │   │   ├── capture_service.py          CaptureSession management
│   │   │   ├── ingestion_service.py        File ingestion + validation
│   │   │   ├── agent_orchestrator.py       OODA loop controller
│   │   │   ├── review_service.py           Review queue management
│   │   │   ├── continuity_service.py       Cross-meeting ActionItem tracking
│   │   │   ├── knowledge_service.py        KnowledgeItems + Terminology
│   │   │   ├── artifact_service.py         Artifact generation dispatch
│   │   │   └── query_service.py            Ask the Meeting execution
│   │   │
│   │   ├── pipeline/                       Processing pipeline stages
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py             Pipeline stage sequencer
│   │   │   ├── stage_base.py               Abstract PipelineStage base class
│   │   │   │
│   │   │   ├── asr/                        ASR (Layer 2 — Perception)
│   │   │   │   ├── asr_adapter.py          Abstract ASRAdapter interface
│   │   │   │   ├── whisper_local.py        WhisperLocalAdapter
│   │   │   │   ├── whisper_api.py          WhisperAPIAdapter
│   │   │   │   └── stub_asr.py             StubASRAdapter (dev/test)
│   │   │   │
│   │   │   ├── diarization/                Diarization (Layer 2 — Perception)
│   │   │   │   ├── diarization_adapter.py  Abstract DiarizationAdapter
│   │   │   │   ├── pyannote_adapter.py     PyannoteAdapter
│   │   │   │   └── stub_diarization.py     StubDiarizationAdapter
│   │   │   │
│   │   │   ├── normalization/              Normalization (Layer 2)
│   │   │   │   └── normalizer.py           TranscriptSegment normalizer
│   │   │   │
│   │   │   ├── llm/                        LLM abstraction (Layers 4-5)
│   │   │   │   ├── llm_adapter.py          Abstract LLMAdapter interface
│   │   │   │   ├── openai_adapter.py       OpenAIAdapter
│   │   │   │   ├── anthropic_adapter.py    AnthropicAdapter
│   │   │   │   ├── ollama_adapter.py       OllamaAdapter (local)
│   │   │   │   └── stub_llm.py             StubLLMAdapter
│   │   │   │
│   │   │   ├── semantic/                   Semantic extraction (Layer 4)
│   │   │   │   ├── semantic_engine.py      Orchestrates all extractors
│   │   │   │   ├── decision_extractor.py
│   │   │   │   ├── action_extractor.py
│   │   │   │   ├── question_extractor.py
│   │   │   │   └── contradiction_detector.py
│   │   │   │
│   │   │   ├── identity/                   Identity resolution (Layer 3)
│   │   │   │   ├── speaker_resolver.py     Speaker ↔ Participant mapping
│   │   │   │   └── entity_resolver.py      Entity/name resolution
│   │   │   │
│   │   │   ├── validation/                 Validation (Layer 6)
│   │   │   │   ├── grounding_validator.py  Evidence link verification
│   │   │   │   └── confidence_scorer.py    Field-level confidence
│   │   │   │
│   │   │   └── world_model/                World model (Layer 5-7)
│   │   │       └── world_model_builder.py  Assembles MeetingRecord
│   │   │
│   │   ├── artifact_generators/            Artifact generation (Layer 10)
│   │   │   ├── docx_generator.py           python-docx
│   │   │   └── pdf_generator.py            WeasyPrint → fallback reportlab
│   │   │
│   │   └── overlay/                        Desktop overlay (Layer 9)
│   │       ├── overlay_manager.py          pywebview launcher
│   │       ├── audio_capture.py            sounddevice WASAPI capture
│   │       ├── hotkey_manager.py           keyboard lib global shortcuts
│   │       └── static/
│   │           ├── overlay.html
│   │           ├── overlay.css
│   │           └── overlay.js
│   │
│   └── storage/                            Local file storage (gitignored)
│       ├── .gitkeep
│       ├── audio/                          Uploaded/recorded audio files
│       ├── artifacts/                      Generated DOCX/PDF/JSON
│       └── imports/                        Imported files
│
└── frontend/                               React + TypeScript (Vite)
    ├── index.html
    ├── package.json
    ├── tsconfig.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx
        ├── App.tsx                         Router + global layout
        │
        ├── types/                          TypeScript domain types
        │   ├── meeting.ts
        │   ├── capture.ts
        │   ├── transcript.ts
        │   ├── evidence.ts
        │   ├── semantic.ts
        │   ├── decisions.ts
        │   ├── actions.ts
        │   ├── review.ts
        │   └── processing.ts
        │
        ├── api/                            API client layer
        │   ├── client.ts                   axios instance + interceptors
        │   ├── meetings.ts
        │   ├── capture.ts
        │   ├── processing.ts
        │   ├── review.ts
        │   ├── artifacts.ts
        │   └── ws.ts                       WebSocket client
        │
        ├── store/                          Zustand state management
        │   ├── meetingStore.ts
        │   ├── captureStore.ts
        │   ├── processingStore.ts
        │   └── reviewStore.ts
        │
        ├── components/
        │   ├── layout/
        │   │   ├── AppShell.tsx            Nav + main area
        │   │   ├── Sidebar.tsx
        │   │   └── TopBar.tsx
        │   ├── capture/
        │   │   ├── CaptureModeSelector.tsx
        │   │   └── AudioSourceIndicator.tsx
        │   ├── meeting/
        │   │   ├── MeetingCard.tsx
        │   │   ├── MeetingStatus.tsx
        │   │   └── QualityMetrics.tsx
        │   ├── transcript/
        │   │   ├── TranscriptView.tsx
        │   │   └── TranscriptSegment.tsx
        │   ├── evidence/
        │   │   ├── EvidencePanel.tsx
        │   │   └── EvidenceCard.tsx
        │   ├── semantic/
        │   │   ├── DecisionCard.tsx
        │   │   ├── ActionItemCard.tsx
        │   │   └── ContradictionAlert.tsx
        │   ├── timeline/
        │   │   └── SemanticTimeline.tsx
        │   ├── review/
        │   │   ├── ReviewQueue.tsx
        │   │   └── ReviewItemCard.tsx
        │   └── agent-console/
        │       └── AgentConsole.tsx
        │
        ├── pages/
        │   ├── Dashboard.tsx
        │   ├── Meetings.tsx
        │   ├── NewMeeting.tsx
        │   ├── MeetingWorkspace.tsx        Central workspace
        │   ├── ActionItems.tsx
        │   ├── Decisions.tsx
        │   ├── People.tsx
        │   ├── Knowledge.tsx
        │   ├── Settings.tsx
        │   └── AgentConsole.tsx
        │
        └── styles/
            ├── index.css                   Design tokens + global styles
            └── components.css
```

---

## Key File Relationships

| If you're looking for... | Go to... |
|---|---|
| Domain entity definitions | `docs/DATA_AND_PROVENANCE_MODEL.md` |
| DB ORM models | `backend/app/models/` |
| API contracts (types) | `backend/app/schemas/` + `frontend/src/types/` |
| Pipeline stage logic | `backend/app/pipeline/` |
| Adding a new LLM provider | Implement `LLMAdapter` in `backend/app/pipeline/llm/` |
| Adding a new ASR provider | Implement `ASRAdapter` in `backend/app/pipeline/asr/` |
| Processing state | `backend/app/services/agent_orchestrator.py` |
| Review queue logic | `backend/app/services/review_service.py` |
| DOCX/PDF generation | `backend/app/artifact_generators/` |
| UI pages | `frontend/src/pages/` |
| UI design tokens | `frontend/src/styles/index.css` |
| Architecture decisions | `docs/adr/` |
