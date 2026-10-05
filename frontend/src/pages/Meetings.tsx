import { MOCK_MEETINGS, statusBadgeClass, confidenceClass, confidenceLabel } from '../mockData'
import { useNavigate } from 'react-router-dom'

export default function Meetings() {
  const navigate = useNavigate()
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>Meetings</h1>
          <p className="text-muted text-xs mt-2">{MOCK_MEETINGS.length} meetings · Phase 0 mock data</p>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/meetings/new')}>
          + New Meeting
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {MOCK_MEETINGS.map(m => (
          <div key={m.id} className="card" style={{ cursor: 'pointer' }} onClick={() => navigate(`/meetings/${m.id}`)}>
            <div className="flex items-center gap-4">
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-md)', fontWeight: 600, marginBottom: 4 }}>{m.title}</div>
                <div className="flex gap-3 items-center">
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {new Date(m.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}
                  </span>
                  <span className={`badge ${m.capture_mode === 'IMPORT' ? 'badge-blue' : m.capture_mode === 'OVERLAY' ? 'badge-green' : 'badge-gray'}`}>
                    {m.capture_mode}
                  </span>
                  <span className={`badge ${statusBadgeClass(m.lifecycle_status)}`}>{m.lifecycle_status}</span>
                  <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{m.privacy_mode}</span>
                </div>
              </div>

              {/* Quality metrics mini-view */}
              <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                {[
                  { label: 'Transcript', key: 'transcript_quality' },
                  { label: 'Speaker', key: 'speaker_attribution_quality' },
                  { label: 'Decisions', key: 'decision_certainty' },
                  { label: 'Grounding', key: 'grounding_coverage' },
                ].map(({ label, key }) => {
                  const val = (m.quality_metrics as any)[key] as number
                  return (
                    <div key={key} style={{ textAlign: 'center' }}>
                      <div className={`confidence ${confidenceClass(val)}`} style={{ justifyContent: 'center', marginBottom: 2 }}>
                        <div className="confidence-dot" />
                        <span>{val > 0 ? confidenceLabel(val) : '—'}</span>
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{label}</div>
                    </div>
                  )
                })}
              </div>

              <span style={{ color: 'var(--text-muted)', fontSize: 18 }}>›</span>
            </div>

            {m.quality_metrics.weak_areas.length > 0 && (
              <div style={{ marginTop: 12, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                {m.quality_metrics.weak_areas.map(w => (
                  <span key={w} className="badge badge-yellow" style={{ fontWeight: 400, textTransform: 'none', letterSpacing: 0 }}>
                    ⚠ {w}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
