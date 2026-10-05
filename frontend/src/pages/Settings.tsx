export default function Settings() {
  return (
    <div style={{ maxWidth: 600 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Settings</h1>
        <p className="text-muted text-xs mt-2">Provider configuration, confidence thresholds, privacy mode.</p>
      </div>

      {[
        { section: 'Providers', rows: [
          { label: 'LLM Provider', value: 'stub', note: 'Set LLM_PROVIDER in .env' },
          { label: 'ASR Provider', value: 'stub', note: 'Set ASR_PROVIDER in .env' },
          { label: 'Diarization Provider', value: 'stub', note: 'Set DIARIZATION_PROVIDER in .env' },
        ]},
        { section: 'Confidence Thresholds', rows: [
          { label: 'Auto-accept threshold', value: '90%', note: 'MIN_AUTO_ACCEPT_CONFIDENCE' },
          { label: 'Surface for review threshold', value: '60%', note: 'MIN_REVIEW_SURFACE_CONFIDENCE' },
        ]},
        { section: 'Privacy', rows: [
          { label: 'Default Privacy Mode', value: 'LOCAL', note: 'DEFAULT_PRIVACY_MODE' },
          { label: 'Storage Root', value: './storage', note: 'STORAGE_ROOT' },
        ]},
        { section: 'Current Phase', rows: [
          { label: 'Phase', value: '0 — Scaffold', note: 'See CAPABILITIES.md' },
          { label: 'API', value: 'http://localhost:8000', note: '' },
          { label: 'Frontend', value: 'http://localhost:5173', note: '' },
        ]},
      ].map(({ section, rows }) => (
        <div key={section} className="card mb-4">
          <div className="card-title mb-4">{section}</div>
          {rows.map(r => (
            <div key={r.label} className="console-row" style={{ padding: '10px 0' }}>
              <div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-primary)', fontWeight: 500 }}>{r.label}</div>
                {r.note && <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{r.note}</div>}
              </div>
              <span className="badge badge-gray">{r.value}</span>
            </div>
          ))}
        </div>
      ))}

      <div style={{ padding: '12px 16px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
        Edit <strong style={{ color: 'var(--text-secondary)' }}>backend/.env</strong> to configure providers and thresholds.<br />
        A settings UI with live reload is planned for Phase 2.
      </div>
    </div>
  )
}
