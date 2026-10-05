# ADR-009: Field-Level Confidence Model

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

A single "meeting confidence" score is misleading. A meeting can have excellent transcription (96%) but poor speaker attribution (61%). Aggregating these into one score hides critical information.

## Decision

Confidence is a **field-level property** on every extracted entity, not a meeting-level summary.

```
TranscriptSegment.asr_confidence
Speaker.resolution_confidence
SemanticEvent.confidence
Decision.confidence
ActionItem.confidence / owner_confidence / deadline_confidence
Contradiction.confidence
KnowledgeItem.confidence
Evidence.confidence
```

`MeetingQualityMetrics` shows these individually (not as one aggregate).

**Routing rules** (configurable thresholds):
- ≥ 0.90: Accept automatically
- 0.75–0.89: Flag for optional review
- 0.60–0.74: Queue for review (medium priority)
- < 0.60: Queue for review (HIGH priority); do NOT surface as verified fact

## Consequences

- Review items are generated per-field, not per-meeting
- The UI shows individual quality scores (Transcript: 96%, Speaker: 61%)
- Low-confidence decisions are never displayed as confirmed without review
- Thresholds are configurable in Settings (not hardcoded)
