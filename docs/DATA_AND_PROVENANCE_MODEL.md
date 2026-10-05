# DATA_AND_PROVENANCE_MODEL.md

> **Version**: 1.0 (Phase 0)  
> **Last updated**: 2026-10-04

---

## 1. Core Principle

Evidence is the authoritative layer. Every extracted claim is traceable to:

| Field | Where Stored |
|---|---|
| Transcript span | `Evidence.timestamp_ms`, `TranscriptSegment.start_ms/end_ms` |
| Speaker | `Evidence.segment_id → TranscriptSegment.speaker_id → Speaker` |
| Timestamp | `Evidence.timestamp_ms` (meeting-relative ms) |
| Source modality | `Evidence.source_type` (TRANSCRIPT / USER_MARK / MANUAL / IMPORT_DOC) |
| Confidence | `Evidence.confidence` (field-level float) |
| Processing stage | `Evidence.processing_run_id → ProcessingRun.stage` |

---

## 2. Domain Model — 22 Persistent Entities

### 2.1 Persistent Entities

These are stored as independent DB rows with their own `id: UUID`.

#### Meeting
```
Meeting
├── id: UUID
├── title: str
├── date: datetime
├── capture_mode: CaptureMode (RECORDING|OVERLAY|IMPORT|NOTES_ONLY)
├── lifecycle_status: MeetingLifecycle (PREPARING→FINALIZED→FOLLOW_UP)
├── processing_status: ProcessingStatus (IDLE|QUEUED|RUNNING|COMPLETE|FAILED)
├── privacy_mode: PrivacyMode (LOCAL|CLOUD|HYBRID)
├── briefing_id: UUID | None
├── quality_metrics: JSON (MeetingQualityMetrics value object)
└── created_at / updated_at
```

#### MeetingSession
```
MeetingSession
├── id: UUID
├── meeting_id: UUID → Meeting
├── started_at: datetime
├── ended_at: datetime | None
└── session_type: (LIVE|IMPORT|REVIEW)
```

#### CaptureSession
```
CaptureSession
├── id: UUID
├── meeting_id: UUID
├── capture_mode: CaptureMode
├── audio_source_state: AudioSourceState
├── audio_source_status: JSON (AudioSourceStatus value object)
├── privacy_mode: PrivacyMode
├── evidence_manifest: JSON (EvidenceManifest value object)
│   ├── available_sources: list[str]
│   ├── unavailable_sources: list[str]
│   └── degradation_reason: str | None
├── started_at / ended_at
└── is_active: bool
```

#### CaptureSource
```
CaptureSource
├── id: UUID
├── capture_session_id: UUID
├── source_type: (MICROPHONE|SYSTEM_AUDIO|IMPORT_FILE|MANUAL)
├── status: (ACTIVE|FAILED|PAUSED|UNAVAILABLE)
├── device_name: str | None
├── file_path: str | None
└── degradation_reason: str | None
```

#### Participant
```
Participant
├── id: UUID
├── meeting_id: UUID
├── name: str
├── email: str | None
├── aliases: JSON list[str]
├── role: str | None
└── is_self: bool  (marks the user running the system)
```

#### Speaker
```
Speaker
├── id: UUID
├── meeting_id: UUID
├── label: str  (e.g. "SPEAKER_1" → resolved to "Akhilesh")
├── resolved_participant_id: UUID | None
├── resolution_confidence: float  (field-level)
├── resolution_source: (HUMAN|SYSTEM|INFERRED)
└── total_speaking_time_ms: int
```

#### TranscriptSegment
```
TranscriptSegment
├── id: UUID
├── meeting_id: UUID
├── speaker_id: UUID | None
├── start_ms: int
├── end_ms: int
├── text: str
├── language: str
├── asr_confidence: float  (field-level)
├── is_edited: bool
├── edited_by: (HUMAN|SYSTEM) | None
└── source_modality: (AUDIO|MANUAL|IMPORT)
```

#### Evidence
```
Evidence
├── id: UUID
├── meeting_id: UUID
├── segment_id: UUID | None       → TranscriptSegment
├── user_mark_id: UUID | None     → UserMark
├── processing_run_id: UUID | None → ProcessingRun
├── source_type: (TRANSCRIPT|USER_MARK|MANUAL|IMPORT_DOC|HUMAN_CORRECTION)
├── source_modality: str
├── timestamp_ms: int | None
├── raw_text: str
├── confidence: float
└── is_immutable: bool = True

IMPORTANT: Evidence records are immutable once stored.
Corrections create new Evidence records with source_type=HUMAN_CORRECTION.
The correcting entity (Decision, ActionItem, etc.) is updated to point to the new Evidence record.
```

#### SemanticEvent
```
SemanticEvent
├── id: UUID
├── meeting_id: UUID
├── event_type: SemanticEventType
│   (IDEA|SUGGESTION|OPINION|DISCUSSION|
│    DECISION_CANDIDATE|DECISION_CONFIRMED|
│    COMMITMENT|ACTION_ITEM|QUESTION|ANSWER|
│    BLOCKER|RISK|DEADLINE|STATUS_UPDATE|
│    DISAGREEMENT|CONTRADICTION|USER_MARK)
├── text: str
├── evidence_ids: JSON list[UUID]  ← MUST be non-empty
├── start_ms: int | None
├── end_ms: int | None
├── confidence: float
├── extraction_stage: str          ← which ProcessingRun
└── review_state: (PENDING|CONFIRMED|REJECTED|UNCERTAIN)
```

#### Decision
```
Decision
├── id: UUID
├── meeting_id: UUID
├── semantic_event_id: UUID
├── text: str
├── status: (CANDIDATE|CONFIRMED|UNRESOLVED|OVERRIDDEN)
├── evidence_ids: JSON list[UUID]  ← MUST be non-empty
├── confidence: float
├── review_state: ReviewState
└── overridden_by_meeting_id: UUID | None
```

#### ActionItem
```
ActionItem
├── id: UUID
├── originating_meeting_id: UUID   ← persists across meetings
├── originating_timestamp_ms: int | None
├── task: str
├── owner_id: UUID | None          → Participant
├── owner_confidence: float        ← field-level
├── deadline: date | None
├── deadline_confidence: float     ← field-level
├── status: (PENDING|IN_PROGRESS|COMPLETED|BLOCKED|CANCELLED)
├── priority: (LOW|MEDIUM|HIGH|CRITICAL)
├── evidence_ids: JSON list[UUID]  ← MUST be non-empty
├── confidence: float
├── review_state: ReviewState
└── last_updated_meeting_id: UUID | None  ← continuity
```

#### Question
```
Question
├── id: UUID
├── meeting_id: UUID
├── text: str
├── asker_id: UUID | None
├── answered: bool
├── answer_text: str | None
├── evidence_ids: JSON list[UUID]
└── confidence: float
```

#### Contradiction
```
Contradiction
├── id: UUID
├── meeting_id: UUID | None        ← None for cross-meeting contradictions
├── event_a_id: UUID               → SemanticEvent or Decision
├── event_b_id: UUID
├── description: str
├── contradiction_type: (DEADLINE|DECISION|OWNER|FACTUAL|CROSS_MEETING)
├── is_cross_meeting: bool
├── meeting_a_id: UUID | None
├── meeting_b_id: UUID | None
├── review_state: ReviewState
└── confidence: float
```

#### MeetingTopic
```
MeetingTopic
├── id: UUID
├── meeting_id: UUID
├── title: str
├── start_ms: int
├── end_ms: int
└── importance: float
```

#### KnowledgeItem
```
KnowledgeItem
├── id: UUID
├── type: (FACT|DECISION|TERMINOLOGY|PERSON|PROJECT|ACRONYM|PATTERN)
├── content: str
├── source_meeting_ids: JSON list[UUID]
├── confidence: float
├── verified: bool
│   ← True ONLY with human confirmation OR system confidence ≥ threshold
│   ← INFERRED alone is NEVER sufficient to set verified=True
├── verification_source: (HUMAN|SYSTEM|INFERRED)
└── created_at
```

#### TerminologyEntry
```
TerminologyEntry
├── id: UUID
├── term: str
├── canonical_meaning: str
├── aliases: JSON list[str]
├── source_meeting_ids: JSON list[UUID]
├── confidence: float
└── verified: bool
```

#### ReviewItem
```
ReviewItem
├── id: UUID
├── meeting_id: UUID
├── type: (SPEAKER_IDENTITY|AMBIGUOUS_DEADLINE|UNCERTAIN_OWNER|
│         CONTRADICTORY_DECISION|UNCLEAR_ACTION|AMBIGUOUS_METADATA|
│         LOW_CONFIDENCE_DECISION|CROSS_MEETING_CONTRADICTION)
├── question: str
├── options: JSON list[str]
├── context: str  ← evidence + rationale; NOT chain-of-thought
├── evidence_ids: JSON list[UUID]
├── priority_score: float  = importance × uncertainty × impact
├── status: (PENDING|RESOLVED|SKIPPED|DEFERRED)
├── resolution: str | None
└── created_at
```

#### ProcessingRun
```
ProcessingRun
├── id: UUID
├── meeting_id: UUID
├── stage: str  (ASR|DIARIZATION|IDENTITY|SEMANTIC|VALIDATION|WORLD_MODEL|ARTIFACT)
├── status: (QUEUED|RUNNING|COMPLETE|FAILED|SKIPPED|INVALIDATED)
├── skip_reason: str | None
├── model_used: str | None
├── adapter_used: str
├── latency_ms: int | None
├── cost_estimate_usd: float | None
├── reason: str
├── input_evidence_ids: JSON list[UUID]
├── output_evidence_ids: JSON list[UUID]
├── input_hash: str | None          ← SHA-256; enables idempotency
├── depends_on_stages: JSON list[str]  ← for dependency-aware invalidation
├── invalidated_at: datetime | None
├── invalidation_reason: str | None
└── started_at / ended_at
```

#### ProcessingLedger
```
ProcessingLedger
├── id: UUID
├── meeting_id: UUID (unique)
├── total_cost_estimate_usd: float
├── total_latency_ms: int
├── stages_run: JSON list[str]
├── stages_skipped: JSON list[str]
└── updated_at
```

#### Artifact
```
Artifact
├── id: UUID
├── meeting_id: UUID
├── type: (DOCX|PDF|JSON|CSV|TRANSCRIPT_TXT|EVIDENCE_JSON)
├── status: ArtifactStatus (CURRENT|STALE|GENERATING|FAILED)
├── path: str  ← relative to storage root
├── file_size_bytes: int
├── generated_at: datetime
├── stale_since: datetime | None
├── stale_reason: str | None
└── generation_run_id: UUID | None
```

#### MeetingBrief
```
MeetingBrief
├── id: UUID
├── meeting_id: UUID
├── title: str
├── previous_meeting_ids: JSON list[UUID]
├── open_action_item_ids: JSON list[UUID]
├── expected_topics: JSON list[str]
├── relevant_documents: JSON list[str]
├── unresolved_question_ids: JSON list[UUID]
└── generated_at: datetime
```

#### UserMark
```
UserMark
├── id: UUID
├── meeting_id: UUID
├── capture_session_id: UUID
├── timestamp_ms: int              ← meeting-relative
├── wall_clock_time: datetime
├── event_type: SemanticEventType  ← e.g. USER_MARK, ACTION_ITEM, DECISION
├── optional_text: str | None
├── source: str = "HUMAN"         ← always HUMAN; immutable
└── processing_priority: float    ← 0.0–1.0; influences pipeline scheduling
```

---

## 3. Value Objects (not independently persisted)

| Value Object | Embedded In | Notes |
|---|---|---|
| `MeetingRecord` | Runtime aggregate | Never stored as a DB table; assembled on demand |
| `MeetingQualityMetrics` | `Meeting.quality_metrics` (JSON) | Field-level quality scores |
| `EvidenceManifest` | `CaptureSession.evidence_manifest` (JSON) | Available/unavailable sources |
| `AudioSourceStatus` | `CaptureSession.audio_source_status` (JSON) | Live source state |
| `TimelineEntry` | Derived from `SemanticEvent` at query time | Not stored |
| `AnswerSource` | Transient query result | Used in Ask-the-Meeting responses |

---

## 4. Stage Dependency Graph

```
ASR ──────────────────────────────────────────────────────────────────┐
 └─► DIARIZATION ──────────────────────────────────────────────────── │
       └─► IDENTITY ──────────────────────────────────────────────── │
              └─► SEMANTIC ──────────────────────────────────────────│
                    └─► VALIDATION ──────────────────────────────────│
                          └─► WORLD_MODEL ──────────────────────────┘
                                └─► ARTIFACTS (CURRENT → STALE → regenerate)
```

---

## 5. Provenance Chain Example

```
Raw audio file (48-minute recording)
  │
  └─► ProcessingRun{stage=ASR, adapter=WhisperLocalAdapter, latency=120s}
        │
        └─► TranscriptSegment{
              id=seg-001, start_ms=2534000, end_ms=2551000,
              text="Let's use PostgreSQL for this.",
              asr_confidence=0.94,
              speaker_id=spk-002
            }
              │
              └─► Evidence{
                    id=ev-001, source_type=TRANSCRIPT,
                    segment_id=seg-001, timestamp_ms=2534000,
                    raw_text="Let's use PostgreSQL for this.",
                    confidence=0.94
                  }
                    │
                    └─► SemanticEvent{
                          type=DECISION_CANDIDATE,
                          evidence_ids=[ev-001],
                          confidence=0.87
                        }
                          │
                          └─► Decision{
                                text="Use PostgreSQL",
                                status=CONFIRMED,
                                evidence_ids=[ev-001],
                                confidence=0.91
                              }
```

---

## 6. Correction Flow

```
Human corrects speaker: SPEAKER_2 → "Priya"
  │
  ├─► Create new Evidence{source_type=HUMAN_CORRECTION, raw_text="SPEAKER_2=Priya"}
  │
  ├─► Update Speaker{label=SPEAKER_2, resolved_participant_id=priya-id,
  │                  resolution_source=HUMAN, resolution_confidence=1.0}
  │
  ├─► Invalidate ProcessingRun{stage=IDENTITY}
  │       + downstream: SEMANTIC, VALIDATION, WORLD_MODEL
  │
  ├─► Mark Artifact{status=STALE, stale_reason="Speaker correction applied"}
  │
  └─► Re-run: IDENTITY → SEMANTIC → VALIDATION → WORLD_MODEL → regenerate DOCX/PDF
       ASR: UNTOUCHED (input_hash unchanged)
       TranscriptSegments: UNTOUCHED
       Original Evidence: UNTOUCHED
```
