import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MOCK_MEETINGS,
  MOCK_ACTIONS,
  MOCK_DECISIONS,
  MOCK_REVIEW_ITEMS,
  statusBadgeClass,
  confidenceClass,
  confidenceLabel,
} from '../mockData'

export default function Dashboard() {
  const navigate = useNavigate()
  const [meetings, setMeetings] = useState<any[]>([])
  const [hasLoadedOnce, setHasLoadedOnce] = useState(false)

  const fetchMeetings = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/meetings/')
      if (res.ok) {
        const data = await res.json()
        setMeetings(data)
      } else {
        setMeetings(MOCK_MEETINGS)
      }
    } catch {
      // Offline fallback
      setMeetings(MOCK_MEETINGS)
    } finally {
      setHasLoadedOnce(true)
    }
  }

  useEffect(() => {
    fetchMeetings()
  }, [])

  const pendingActions = MOCK_ACTIONS.filter(
    (a) => a.status === 'PENDING' || a.status === 'IN_PROGRESS'
  )
  const pendingReviews = MOCK_REVIEW_ITEMS
  const recentMeetings = meetings.slice(0, 4)

  const handleUseDemoMeeting = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/meetings/demo-meeting-arch-review-001')
      if (res.ok) {
        navigate('/meetings/demo-meeting-arch-review-001')
        return
      }
    } catch {}
    navigate('/meetings/demo-meeting-arch-review-001')
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, marginBottom: 4 }}>
            Meeting Intelligence
          </h1>
          <p className="text-secondary text-sm">Evidence-grounded — every claim is traceable</p>
        </div>
        <div className="flex gap-2">
          <button className="btn btn-secondary btn-sm" onClick={handleUseDemoMeeting}>
            ★ View Demo Review
          </button>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('/meetings/new')}>
            + New Meeting
          </button>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="grid-4 mb-6">
        <div className="metric-card">
          <div className="metric-label">Meetings</div>
          <div className="metric-value">{meetings.length}</div>
          <div className="metric-change">
            {meetings.some((m) => m.title?.includes('[DEMO DATA]')) ? '1 demo active' : 'Live database'}
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Open Actions</div>
          <div className="metric-value" style={{ color: 'var(--warning)' }}>
            {pendingActions.length}
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            across {meetings.length || 1} meetings
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Decisions</div>
          <div className="metric-value">{MOCK_DECISIONS.length}</div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            {MOCK_DECISIONS.filter((d) => d.status === 'UNRESOLVED').length} unresolved
          </div>
        </div>
        <div className="metric-card">
          <div className="metric-label">Needs Review</div>
          <div
            className="metric-value"
            style={{ color: pendingReviews.length > 0 ? 'var(--error)' : 'var(--success)' }}
          >
            {pendingReviews.length}
          </div>
          <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
            review items pending
          </div>
        </div>
      </div>

      {/* Empty State Guard — If there are NO meetings in DB */}
      {hasLoadedOnce && meetings.length === 0 ? (
        <div
          className="card mb-6"
          style={{
            padding: '40px 24px',
            textAlign: 'center',
            background: 'var(--bg-card)',
            border: '1px dashed var(--border)',
          }}
        >
          <div style={{ fontSize: 36, marginBottom: 12 }}>📋</div>
          <h2 style={{ fontSize: 'var(--text-lg)', fontWeight: 700, marginBottom: 6 }}>
            NO MEETINGS YET
          </h2>
          <p className="text-muted text-sm mb-6" style={{ maxWidth: 500, margin: '0 auto 24px' }}>
            Get started right away by capturing a live discussion, importing an existing recording, or inspecting our pre-seeded product architecture demo.
          </p>

          <div
            style={{
              display: 'flex',
              gap: 12,
              justifyContent: 'center',
              flexWrap: 'wrap',
              maxWidth: 720,
              margin: '0 auto',
            }}
          >
            <button className="btn btn-primary" onClick={() => navigate('/meetings/new')}>
              + New Meeting
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/meetings/new?mode=IMPORT')}
            >
              ⬆ Upload a recording
            </button>
            <button
              className="btn btn-secondary"
              onClick={() =>
                window.open(
                  '/overlay',
                  'MoMOverlay',
                  'width=440,height=680,top=100,left=100,resizable=yes'
                )
              }
            >
              ⚡ Start overlay
            </button>
            <button
              className="btn btn-secondary"
              onClick={() => navigate('/meetings/new?mode=IMPORT')}
            >
              📄 Import transcript
            </button>
            <button className="btn btn-secondary" onClick={handleUseDemoMeeting}>
              ★ Use demo meeting
            </button>
          </div>
        </div>
      ) : (
        <div className="grid-2 gap-4">
          {/* Recent Meetings */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Recent Meetings</div>
              <a href="/meetings" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>
                View all →
              </a>
            </div>
            {recentMeetings.map((m) => {
              const isDemo = m.title?.includes('[DEMO DATA]') || m.id === 'demo-meeting-arch-review-001'
              return (
                <div
                  key={m.id}
                  onClick={() => navigate(`/meetings/${m.id}`)}
                  style={{
                    padding: '12px 0',
                    borderBottom: '1px solid var(--border-subtle)',
                    cursor: 'pointer',
                  }}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          style={{
                            fontSize: 'var(--text-sm)',
                            fontWeight: 600,
                            color: 'var(--text-primary)',
                          }}
                        >
                          {m.title}
                        </span>
                        {isDemo && (
                          <span
                            style={{
                              fontSize: 9,
                              fontWeight: 700,
                              padding: '1px 6px',
                              borderRadius: 4,
                              background: 'rgba(234, 179, 8, 0.15)',
                              color: '#eab308',
                              border: '1px solid rgba(234, 179, 8, 0.3)',
                              letterSpacing: '0.04em',
                            }}
                          >
                            DEMO DATA
                          </span>
                        )}
                      </div>
                      <div
                        style={{
                          fontSize: 'var(--text-xs)',
                          color: 'var(--text-muted)',
                          marginTop: 2,
                        }}
                      >
                        {m.date ? new Date(m.date).toLocaleDateString() : 'Recent'} · {m.capture_mode || 'IMPORT'}
                      </div>
                    </div>
                    <span className={`badge ${statusBadgeClass(m.lifecycle_status || 'FINALIZED')}`}>
                      {m.lifecycle_status || 'FINALIZED'}
                    </span>
                  </div>
                  <div style={{ marginTop: 8 }}>
                    <QualityMini metrics={m.quality_metrics || { transcript_quality: 0.96, grounding_coverage: 1.0 }} />
                  </div>
                </div>
              )
            })}
          </div>

          {/* Review Queue */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Review Queue</div>
              <span className={`badge ${pendingReviews.length > 0 ? 'badge-red' : 'badge-green'}`}>
                {pendingReviews.length} pending
              </span>
            </div>
            {pendingReviews.length === 0 ? (
              <div className="empty-state" style={{ padding: '32px 0' }}>
                <div className="empty-state-title" style={{ fontSize: 'var(--text-sm)' }}>
                  All caught up!
                </div>
                <div className="empty-state-desc" style={{ fontSize: 'var(--text-xs)' }}>
                  No items need your attention.
                </div>
              </div>
            ) : (
              pendingReviews.map((r) => (
                <div
                  key={r.id}
                  className={`review-item ${r.priority_score >= 0.7 ? 'high-priority' : 'med-priority'}`}
                  style={{ marginBottom: 8 }}
                >
                  <div
                    style={{
                      fontSize: 'var(--text-xs)',
                      color: 'var(--text-muted)',
                      marginBottom: 4,
                      fontWeight: 600,
                    }}
                  >
                    {r.type.replace(/_/g, ' ')} · score {r.priority_score.toFixed(2)}
                  </div>
                  <div className="review-question" style={{ fontSize: 'var(--text-sm)' }}>
                    {r.question}
                  </div>
                  <div className="review-options">
                    {r.options.slice(0, 2).map((o) => (
                      <div key={o} className="review-option">
                        {o}
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Open Actions */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Open Actions</div>
              <a href="/actions" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>
                View all →
              </a>
            </div>
            {pendingActions.map((a) => (
              <div key={a.id} className="action-card">
                <span className="decision-icon">⚡</span>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                    }}
                  >
                    {a.task}
                  </div>
                  <div className="flex gap-2 mt-2" style={{ flexWrap: 'wrap' }}>
                    {a.owner_name && <span className="badge badge-blue">{a.owner_name}</span>}
                    {a.deadline && <span className="badge badge-yellow">Due {a.deadline}</span>}
                    <span className={`badge ${statusBadgeClass(a.priority)}`}>{a.priority}</span>
                  </div>
                </div>
                <div className={`confidence ${confidenceClass(a.confidence)}`}>
                  <div className="confidence-dot" />
                  {confidenceLabel(a.confidence)}
                </div>
              </div>
            ))}
          </div>

          {/* Decisions */}
          <div className="card">
            <div className="card-header">
              <div className="card-title">Recent Decisions</div>
              <a href="/decisions" style={{ fontSize: 'var(--text-xs)', color: 'var(--accent)' }}>
                View all →
              </a>
            </div>
            {MOCK_DECISIONS.map((d) => (
              <div key={d.id} className="decision-card">
                <span className="decision-icon">✓</span>
                <div style={{ flex: 1 }}>
                  <div
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 500,
                      color: 'var(--text-primary)',
                    }}
                  >
                    {d.text}
                  </div>
                  <div className="flex gap-2 mt-2">
                    <span className={`badge ${statusBadgeClass(d.status)}`}>{d.status}</span>
                  </div>
                </div>
                <div className={`confidence ${confidenceClass(d.confidence)}`}>
                  <div className="confidence-dot" />
                  {confidenceLabel(d.confidence)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function QualityMini({ metrics }: { metrics: any }) {
  const bars = [
    { label: 'Transcript', value: metrics?.transcript_quality ?? 0.96 },
    { label: 'Grounding', value: metrics?.grounding_coverage ?? 1.0 },
  ]
  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {bars.map((b) => (
        <div key={b.label} style={{ flex: 1 }}>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>{b.label}</div>
          <div className="quality-track">
            <div
              className={`quality-fill ${b.value >= 0.9 ? 'high' : b.value >= 0.6 ? 'med' : 'low'}`}
              style={{ width: `${b.value * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
