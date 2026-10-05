export default function People() {
  const SPEAKERS = [
    { id: 'spk-0', label: 'SPEAKER_0', resolved: 'Akhilesh', confidence: 0.0, source: 'INFERRED', speaking_pct: 38 },
    { id: 'spk-1', label: 'SPEAKER_1', resolved: null, confidence: 0.0, source: 'INFERRED', speaking_pct: 45 },
    { id: 'spk-2', label: 'SPEAKER_2', resolved: 'Priya', confidence: 0.0, source: 'INFERRED', speaking_pct: 17 },
  ]
  return (
    <div>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>People</h1>
        <p className="text-muted text-xs mt-2">Participants and speaker resolution. Phase 3: diarization + identity resolution.</p>
      </div>
      <div className="card">
        <div style={{ marginBottom: 16, padding: '10px 14px', background: 'var(--accent-dim)', border: '1px solid var(--accent)', borderRadius: 'var(--radius-md)' }}>
          <strong style={{ color: 'var(--accent)', fontSize: 'var(--text-sm)' }}>Phase 3 preview</strong>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginTop: 4 }}>
            Diarization + speaker-to-participant resolution is implemented in Phase 3.
            Below shows Phase 0 mock data.
          </div>
        </div>
        {SPEAKERS.map(s => (
          <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 16, padding: '14px 0', borderBottom: '1px solid var(--border-subtle)' }}>
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'var(--bg-elevated)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16, flexShrink: 0 }}>◎</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)' }}>{s.resolved ?? <span style={{ color: 'var(--text-muted)' }}>{s.label} (unresolved)</span>}</div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{s.label} · {s.speaking_pct}% speaking time</div>
            </div>
            {!s.resolved && <span className="badge badge-red">Needs resolution</span>}
            {s.resolved && <span className="badge badge-yellow">Inferred — needs confirmation</span>}
            <button className="btn btn-secondary btn-sm">Identify →</button>
          </div>
        ))}
      </div>
    </div>
  )
}
