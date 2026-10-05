export default function Knowledge() {
  const ITEMS = [
    { type: 'DECISION', content: 'Use FastAPI for backend framework', confidence: 0.92, verified: true, source: 'HUMAN', meetings: 1 },
    { type: 'DECISION', content: 'PostgreSQL as primary database', confidence: 0.88, verified: true, source: 'HUMAN', meetings: 1 },
    { type: 'FACT', content: 'Team is familiar with FastAPI', confidence: 0.75, verified: false, source: 'INFERRED', meetings: 1 },
    { type: 'PERSON', content: 'Akhilesh: Backend lead', confidence: 0.95, verified: false, source: 'INFERRED', meetings: 1 },
  ]
  const TERMS = [
    { term: 'MoM', canonical_meaning: 'Minutes of Meeting', aliases: ['Meeting Minutes'], verified: true },
    { term: 'FastAPI', canonical_meaning: 'Python async web framework', aliases: [], verified: true },
    { term: 'WASAPI', canonical_meaning: 'Windows Audio Session API — used for system audio loopback', aliases: [], verified: false },
  ]

  return (
    <div>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Knowledge Base</h1>
        <p className="text-muted text-xs mt-2">Persistent organizational memory accreted across meetings. Phase 6: full cross-meeting continuity.</p>
      </div>

      <div className="grid-2 gap-4">
        <div>
          <div style={{ fontWeight: 700, marginBottom: 12, fontSize: 'var(--text-md)' }}>Knowledge Items</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12 }}>
            Items marked <strong>INFERRED</strong> are never promoted to verified without human confirmation.
          </div>
          {ITEMS.map((item, i) => (
            <div key={i} className="card mb-2">
              <div className="flex gap-2 mb-2">
                <span className="badge badge-blue">{item.type}</span>
                {item.verified ? <span className="badge badge-green">✓ Verified</span> : <span className="badge badge-yellow">Inferred</span>}
                <span style={{ fontSize: 10, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginLeft: 'auto' }}>
                  {Math.round(item.confidence * 100)}%
                </span>
              </div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>{item.content}</div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>Source: {item.source} · {item.meetings} meeting{item.meetings !== 1 ? 's' : ''}</div>
              {!item.verified && <button className="btn btn-primary btn-sm mt-2">Confirm</button>}
            </div>
          ))}
        </div>

        <div>
          <div style={{ fontWeight: 700, marginBottom: 12, fontSize: 'var(--text-md)' }}>Terminology Dictionary</div>
          {TERMS.map((t, i) => (
            <div key={i} className="card mb-2">
              <div className="flex items-center gap-2 mb-1">
                <span style={{ fontWeight: 700, fontSize: 'var(--text-sm)' }}>{t.term}</span>
                {t.verified ? <span className="badge badge-green">✓</span> : <span className="badge badge-yellow">Unverified</span>}
              </div>
              <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>{t.canonical_meaning}</div>
              {t.aliases.length > 0 && <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>Also: {t.aliases.join(', ')}</div>}
            </div>
          ))}
          <button className="btn btn-secondary btn-sm mt-2">+ Add Term</button>
        </div>
      </div>
    </div>
  )
}
