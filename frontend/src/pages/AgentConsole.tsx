export default function AgentConsole() {
  const STATE = {
    current_state: 'IDLE',
    current_stage: 'IDLE',
    stages_run: ['ASR', 'DIARIZATION', 'IDENTITY', 'SEMANTIC', 'VALIDATION', 'WORLD_MODEL', 'ARTIFACTS'],
    stages_skipped: [],
  }
  const LEDGER = { total_cost_usd: 0.0, total_latency_ms: 0, stages_run: STATE.stages_run, stages_skipped: STATE.stages_skipped }
  const WORLD = { decisions_total: 3, decisions_confirmed: 2, decisions_candidate: 0, decisions_unresolved: 1, action_items_total: 4, action_items_pending: 3 }
  const INVARIANTS = [
    'Evidence is the ground truth',
    'MeetingRecord is canonical — DOCX/PDF are renderings',
    'Every claim must have at least one evidence reference',
    'Overlay Shell is independent of Capture Controllers',
    'Confidence is field-level, not meeting-level',
    'Corrections create new Evidence — never mutate existing records',
    'Pipeline stages are idempotent (input_hash)',
    'A correction must NOT trigger reprocessing of unrelated stages',
  ]

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Agent Console</h1>
        <p className="text-muted text-xs mt-2">System state, processing ledger, world model. No chain-of-thought exposed.</p>
      </div>

      <div className="grid-2 gap-4 mb-4">
        {/* Agent state */}
        <div className="console-panel">
          <div className="console-header">Agent State</div>
          <div className="console-body">
            {[
              ['Current State', STATE.current_state],
              ['Current Stage', STATE.current_stage],
              ['Stages Run', STATE.stages_run.join(' → ')],
              ['Stages Skipped', STATE.stages_skipped.length > 0 ? STATE.stages_skipped.join(', ') : '—'],
            ].map(([k, v]) => (
              <div key={k} className="console-row">
                <span className="console-key">{k}</span>
                <span className="console-value">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Processing ledger */}
        <div className="console-panel">
          <div className="console-header">Processing Ledger</div>
          <div className="console-body">
            {[
              ['Total Cost', `$${LEDGER.total_cost_usd.toFixed(4)}`],
              ['Total Latency', `${LEDGER.total_latency_ms.toLocaleString()} ms`],
              ['LLM Provider', 'stub (Phase 0)'],
              ['ASR Provider', 'stub (Phase 0)'],
              ['Diarization', 'stub (Phase 0)'],
            ].map(([k, v]) => (
              <div key={k} className="console-row">
                <span className="console-key">{k}</span>
                <span className="console-value">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* World model */}
        <div className="console-panel">
          <div className="console-header">World Model</div>
          <div className="console-body">
            {[
              ['Decisions (total)', WORLD.decisions_total],
              ['  → Confirmed', WORLD.decisions_confirmed],
              ['  → Unresolved', WORLD.decisions_unresolved],
              ['Action Items', WORLD.action_items_total],
              ['  → Pending', WORLD.action_items_pending],
            ].map(([k, v]) => (
              <div key={String(k)} className="console-row">
                <span className="console-key" style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)' }}>{k}</span>
                <span className="console-value">{v}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stage dependency graph */}
        <div className="console-panel">
          <div className="console-header">Stage Dependency Graph</div>
          <div className="console-body">
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', lineHeight: 2 }}>
              ASR<br />
              └→ DIARIZATION<br />
              {'    '}└→ IDENTITY<br />
              {'         '}└→ SEMANTIC<br />
              {'               '}└→ VALIDATION<br />
              {'                      '}└→ WORLD_MODEL<br />
              {'                              '}└→ ARTIFACTS
            </div>
            <div style={{ marginTop: 12, fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              Corrections invalidate only downstream stages. ASR is never re-run unless audio changes.
            </div>
          </div>
        </div>
      </div>

      {/* Architecture invariants */}
      <div className="console-panel">
        <div className="console-header">Architecture Invariants (Active)</div>
        <div className="console-body">
          {INVARIANTS.map((inv, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border-subtle)', fontSize: 'var(--text-xs)' }}>
              <span style={{ color: 'var(--success)', fontFamily: 'var(--font-mono)' }}>[{String(i + 1).padStart(2, '0')}]</span>
              <span style={{ color: 'var(--text-secondary)' }}>{inv}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
