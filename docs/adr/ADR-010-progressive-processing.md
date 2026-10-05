# ADR-010: Progressive Processing

**Date**: 2026-10-04  
**Status**: Accepted

---

## Context

Running the full ML pipeline on every meeting regardless of complexity wastes compute, time, money, and — for user-interrupting operations — human attention.

## Decision

The agent follows a **tiered escalation model**:

| Tier | Mechanism | Cost |
|---|---|---|
| T1 | Deterministic rules (regex, duration, word count) | ~0 |
| T2 | Lightweight ML / heuristics | Low |
| T3 | Small/local LLM | Medium |
| T4 | Strong cloud LLM | High |
| T5 | Human review | Human time |

The agent always tries T1 first and escalates only when T1 is insufficient.

**Skip conditions** (checked via `input_hash` before every stage):
- Output already exists AND input_hash matches → SKIP
- Evidence source unavailable → SKIP + log gap
- Stage not needed for this meeting complexity → SKIP with reason

**Mark Moment priority:** `UserMark.processing_priority` (default 0.9) causes the agent to process marked regions first and with higher-tier reasoning.

## Consequences

- Simple meetings use T3 at most; complex contradictions use T4
- `ProcessingRun.reason` always explains why a stage ran or was skipped
- `ProcessingLedger` tracks cumulative cost for optimization
- Human attention is a first-class resource: `ReviewItem.priority_score = importance × uncertainty × impact`
