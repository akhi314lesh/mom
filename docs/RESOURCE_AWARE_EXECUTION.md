# RESOURCE_AWARE_EXECUTION.md

> **Version**: 1.0  
> **Last updated**: 2026-10-04

---

## 1. Principle

The agent must optimize across multiple scarce resources simultaneously:
- **Compute** (CPU/GPU processing time)
- **API cost** (LLM calls, cloud ASR)
- **Latency** (time to first result)
- **Memory** (large audio/model footprint)
- **Storage** (audio files, artifacts)
- **Human attention** (review items, interruptions)

**Never use a Tier 4 operation when a Tier 1 check can resolve the issue.**

---

## 2. Progressive Escalation Tiers

| Tier | Mechanism | Examples | Cost |
|---|---|---|---|
| T1 | Deterministic rules | Duration check, word count, regex patterns | ~0 |
| T2 | Lightweight ML / heuristics | Keyword extraction, simple classification | Low |
| T3 | Small/local LLM | Semantic classification, short extraction | Medium |
| T4 | Strong cloud LLM | Complex reasoning, contradiction analysis | High |
| T5 | Human review | Unresolvable ambiguity (confidence < 0.60) | Human time |

---

## 3. Stage Skip Conditions

Before executing any stage, check:

| Condition | Action |
|---|---|
| `ProcessingRun.status = COMPLETE` AND `input_hash` matches current inputs | SKIP — reuse outputs |
| Evidence source unavailable (per `EvidenceManifest`) | SKIP — log gap; degrade gracefully |
| Transcript already exists with `asr_confidence > 0.85` | Skip ASR; reuse transcript |
| Speaker identity already confirmed by human | Skip re-diarization for that speaker |
| User marked a specific moment (UserMark with high `processing_priority`) | Prioritize that region |
| Only 1 ambiguous segment | Repair that segment only, not full re-transcription |
| Simple meeting (< 5 speakers, < 30 min, < 50 events) | Use T3 instead of T4 |
| Complex contradiction detected | Escalate to T4 |
| T4 result confidence < 0.60 | Create ReviewItem for human |

---

## 4. Human Attention Budget

The agent must minimize review interruptions.

```
ReviewItem.priority_score = importance × uncertainty × impact

importance = 0.0–1.0  (how central to meeting outcome)
uncertainty = 1.0 − confidence
impact      = 0.0–1.0  (how much wrong answer affects final record)
```

Surfacing rules:
- `priority_score ≥ 0.5` → Surface immediately in review queue
- `priority_score 0.2–0.49` → Queue but don't highlight urgently
- `priority_score < 0.2` → Do not surface unless user requests low-priority review

---

## 5. Processing Ledger

Every ProcessingRun is logged:

```
ProcessingLedger (per meeting):
├── total_cost_estimate_usd: float
├── total_latency_ms: int
├── stages_run: list[str]
└── stages_skipped: list[str]
```

Individual `ProcessingRun`:
```
├── stage: str
├── adapter_used: str
├── latency_ms: int
├── cost_estimate_usd: float
└── reason: str  ← why it ran OR was skipped
```

This ledger enables cost/performance optimization over time.

---

## 6. Invalidation vs. Full Reprocess

When a correction occurs, the system MUST:
1. Identify which stages depend on the corrected layer (via `depends_on_stages`)
2. Set those runs to `INVALIDATED`
3. Mark artifacts as `STALE`
4. Re-run ONLY invalidated stages
5. Regenerate artifacts from updated MeetingRecord (cheap operation)

**NEVER** rerun ASR because an artifact was stale.
**NEVER** rerun the entire pipeline for a speaker name correction.

---

## 7. Mark Moment — Processing Priority

When a user creates a `UserMark` (Ctrl+Shift+M), the marked region is assigned:

```
UserMark.processing_priority = 0.9  (by default)
```

During semantic extraction, regions near UserMarks are processed first. This is an important resource-saving mechanism for long meetings:

```
60-minute meeting:
  User marks 00:42:17
  Agent prioritizes: 00:41:30 – 00:43:00
  → Rich semantic extraction for that region
  → Standard extraction for rest
  → Cheaper overall; faster time-to-result for the important part
```
