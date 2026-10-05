# QUALITY_AND_VALIDATION.md

> **Version**: 1.0  
> **Last updated**: 2026-10-04

---

## 1. Field-Level Confidence Model

Confidence is NOT one number per meeting. Every extracted field carries its own confidence score.

| Field | Entity | Range |
|---|---|---|
| `asr_confidence` | `TranscriptSegment` | 0.0–1.0 |
| `resolution_confidence` | `Speaker` | 0.0–1.0 |
| `confidence` | `SemanticEvent` | 0.0–1.0 |
| `confidence` | `Decision` | 0.0–1.0 |
| `confidence` | `ActionItem` | 0.0–1.0 |
| `owner_confidence` | `ActionItem` | 0.0–1.0 |
| `deadline_confidence` | `ActionItem` | 0.0–1.0 |
| `confidence` | `Contradiction` | 0.0–1.0 |
| `confidence` | `KnowledgeItem` | 0.0–1.0 |
| `confidence` | `Evidence` | 0.0–1.0 |

---

## 2. Confidence → Action Routing

| Confidence | Action |
|---|---|
| ≥ 0.90 | Accept automatically; no review |
| 0.75 – 0.89 | Flag; low-priority review item |
| 0.60 – 0.74 | Queue for review; medium priority |
| < 0.60 | Queue for review; HIGH priority; do not present as fact |

Thresholds are configurable in Settings (`MIN_AUTO_ACCEPT_CONFIDENCE`, etc.).

---

## 3. Meeting Quality Metrics

```
MeetingQualityMetrics (JSON in Meeting.quality_metrics):
├── transcript_quality: float        # mean asr_confidence
├── speaker_attribution_quality: float  # % segments with resolved speaker
├── decision_certainty: float        # mean Decision.confidence
├── action_extraction_confidence: float  # mean ActionItem.confidence
├── grounding_coverage: float        # % events with evidence_ids
├── overall_confidence: float        # weighted mean
└── weak_areas: list[str]            # human-readable descriptions
                                     # e.g. ["2 speakers overlap frequently",
                                     #        "1 deadline ambiguous"]
```

---

## 4. Grounding Validation

The `GroundingValidator` stage checks:

1. Every `SemanticEvent` has ≥ 1 `evidence_ids` entry (data integrity)
2. Every `Decision` has ≥ 1 `evidence_ids` entry
3. Every `ActionItem` has ≥ 1 `evidence_ids` entry
4. Every `Evidence` record references a real `TranscriptSegment` (if TRANSCRIPT type)
5. No `Decision.status = CONFIRMED` without explicit confirmation signal in evidence

Validation failures are logged to the `ProcessingRun` with `status = FAILED`.

---

## 5. Semantic Escalation Invariants

The system MUST enforce these semantic rules:

| From | To | Requires |
|---|---|---|
| `SUGGESTION` | `DECISION_CANDIDATE` | Agreement signal from another participant |
| `OPINION` | `DECISION_CANDIDATE` | Same as above |
| `DECISION_CANDIDATE` | `DECISION_CONFIRMED` | Explicit acceptance signal + no active DISAGREEMENT |
| Any → `DECISION_CONFIRMED` | | No unresolved `Contradiction` on same topic |

Violations of these rules create a `Contradiction` record and a high-priority `ReviewItem`.

---

## 6. Contradiction Detection

### Within-Meeting
- Two `DECISION_CANDIDATE` events with conflicting content
- Two `DEADLINE` events for same task/person with different dates
- Explicit `DISAGREEMENT` speech act
- Two statements attributing same task to different owners

### Cross-Meeting
- New `DECISION_CONFIRMED` conflicts with a previous `DECISION_CONFIRMED`
- New `DEADLINE` conflicts with existing `ActionItem.deadline`

**Resolution rule:** The system ALWAYS prefers `DECISION UNRESOLVED` over arbitrarily choosing one side. Both sides are preserved in evidence.

---

## 7. Evidence Coverage

```
grounding_coverage = (events with ≥1 evidence_id) / (total events)
```

Target: ≥ 0.95 (95% of events must be grounded)

If `grounding_coverage < 0.90`, the system adds a weak area note and creates a `ReviewItem` flagging ungrounded claims.

---

## 8. What the UI Shows

The system exposes evidence and rationale. It does NOT expose chain-of-thought.

```
DECISION
Use PostgreSQL

Confidence: 91%

Evidence:
00:42:17–00:42:31
Speaker: Priya

Transcript:
"...let's use PostgreSQL for this."

[Jump to source]
```

For every item with `confidence < 0.75`, the UI shows a visual indicator (e.g., amber dot) and a "Review this" link.
