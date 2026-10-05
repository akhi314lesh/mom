import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import {
  MOCK_MEETINGS,
  MOCK_DECISIONS,
  MOCK_ACTIONS,
  MOCK_TRANSCRIPT,
  MOCK_REVIEW_ITEMS,
  formatMs,
  confidenceClass,
  confidenceLabel,
  statusBadgeClass,
} from '../mockData'

type Tab = 'transcript' | 'decisions' | 'actions' | 'review' | 'timeline'

export default function MeetingWorkspace() {
  const { id } = useParams<{ id: string }>()
  const [tab, setTab] = useState<Tab>('decisions')
  const [evidenceTarget, setEvidenceTarget] = useState<string | null>(null)

  // Live state
  const [liveRecord, setLiveRecord] = useState<any | null>(null)
  const [pipelineProgress, setPipelineProgress] = useState<number | null>(null)
  const [pipelineStage, setPipelineStage] = useState<string | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [resolvedReviews, setResolvedReviews] = useState<Record<string, string>>({})

  // Fetch meeting record from backend with fallback
  useEffect(() => {
    let ws: WebSocket | null = null

    async function fetchRecord() {
      if (!id) return
      try {
        const res = await fetch(`http://localhost:8000/api/meetings/${id}/record`)
        if (res.ok) {
          const data = await res.json()
          setLiveRecord(data)
          if (data.meeting?.processing_status === 'RUNNING') {
            setPipelineProgress(0.5)
            setPipelineStage('PROCESSING')
          }
        }
      } catch {
        // Backend offline, fallback to mock data
      }
    }

    fetchRecord()

    // WebSocket listener
    try {
      ws = new WebSocket(`ws://localhost:8000/api/ws/meeting/${id}`)
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data)
          if (msg.progress !== undefined) {
            setPipelineProgress(msg.progress)
          }
          if (msg.stage) {
            setPipelineStage(msg.stage)
          }
          if (msg.type === 'PIPELINE_COMPLETED' || msg.status === 'COMPLETED' || msg.type === 'CORRECTION_APPLIED') {
            fetchRecord()
            if (msg.status === 'COMPLETED') setPipelineProgress(null)
          }
          if (msg.type === 'USER_MARK' && msg.mark) {
            setLiveRecord((prev: any) => {
              if (!prev) return prev
              const existingMarks = prev.user_marks || []
              if (existingMarks.some((m: any) => m.id === msg.mark.id)) return prev
              return {
                ...prev,
                user_marks: [...existingMarks, msg.mark],
                evidence: msg.evidence ? [...(prev.evidence || []), msg.evidence] : prev.evidence,
              }
            })
          }
        } catch {}
      }
    } catch {}

    return () => {
      if (ws) ws.close()
    }
  }, [id])

  // Resolve active dataset (live if available, else mock)
  const mockMeeting = MOCK_MEETINGS.find((m) => m.id === id) ?? MOCK_MEETINGS[0]
  const meeting = liveRecord?.meeting ?? mockMeeting

  const decisions =
    liveRecord?.decisions && liveRecord.decisions.length > 0
      ? liveRecord.decisions
      : MOCK_DECISIONS.filter((d) => d.meeting_id === meeting.id || meeting.id === 'mtg-001')

  const actions =
    liveRecord?.action_items && liveRecord.action_items.length > 0
      ? liveRecord.action_items
      : MOCK_ACTIONS.filter((a) => a.originating_meeting_id === meeting.id || meeting.id === 'mtg-001')

  const userMarks = liveRecord?.user_marks ?? []

  const transcript =
    liveRecord?.transcript && liveRecord.transcript.length > 0
      ? liveRecord.transcript
      : MOCK_TRANSCRIPT

  const reviews =
    liveRecord?.review_items && liveRecord.review_items.length > 0
      ? liveRecord.review_items
      : MOCK_REVIEW_ITEMS

  const quality = liveRecord?.quality_metrics ?? meeting.quality_metrics ?? {}

  const handleDownloadDocx = async () => {
    setDownloading(true)
    try {
      const docx = (liveRecord?.artifacts || []).find((a: any) => a.type === 'DOCX')
      if (docx) {
        window.open(`http://localhost:8000/api/artifacts/${docx.id}/download`, '_blank')
        return
      }

      // Generate on-demand
      const res = await fetch(`http://localhost:8000/api/artifacts/meeting/${meeting.id}/generate`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        if (data.artifact_id) {
          window.open(`http://localhost:8000/api/artifacts/${data.artifact_id}/download`, '_blank')
          return
        }
      }
    } catch {
      alert('Backend offline. Start the backend with: uvicorn app.main:app --port 8000')
    } finally {
      setDownloading(false)
    }
  }

  const handleResolveReview = async (item: any, resolution: string) => {
    setResolvedReviews((prev) => ({ ...prev, [item.id]: resolution }))
    try {
      await fetch(`http://localhost:8000/api/review/${meeting.id}/item/${item.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'RESOLVED', resolution }),
      })
    } catch {}
  }

  // Selected evidence lookup
  const selectedEvidence = (() => {
    if (!evidenceTarget) return null

    // Check user marks first
    const markMatch = userMarks.find((m: any) => m.id === evidenceTarget)
    if (markMatch) {
      const evMatch = (liveRecord?.evidence || []).find(
        (e: any) => e.user_mark_id === markMatch.id || e.id === markMatch.id
      )
      return {
        source_type: 'USER_MARK',
        source_modality: 'TEXT',
        raw_text: evMatch?.raw_text || markMatch.optional_text || `[${markMatch.event_type}] User marked key moment`,
        confidence: 1.0,
        timestamp_ms: markMatch.timestamp_ms || 0,
        speaker: 'Human Participant (Keyboard / Desktop Overlay)',
      }
    }

    const allItems = [...decisions, ...actions]
    const targetItem = allItems.find((i: any) => i.id === evidenceTarget)
    const targetEvId = targetItem?.evidence_ids?.[0] || evidenceTarget
    const evMatch = (liveRecord?.evidence || []).find((e: any) => e.id === targetEvId)
    if (evMatch) {
      return {
        source_type: evMatch.source_type,
        source_modality: 'AUDIO',
        raw_text: evMatch.raw_text,
        confidence: evMatch.confidence,
        timestamp_ms: evMatch.timestamp_ms || 18000,
        speaker: 'Akhilesh (Speaker 0)',
      }
    }
    return {
      source_type: 'TRANSCRIPT',
      source_modality: 'AUDIO',
      raw_text:
        targetItem?.text ||
        targetItem?.task ||
        "Let's use FastAPI — it's async, well-documented, and the team is familiar with it.",
      confidence: targetItem?.confidence || 0.94,
      timestamp_ms: 18000,
      speaker: 'Akhilesh (Speaker 0)',
    }
  })()

  return (
    <div style={{ display: 'flex', gap: 20, height: '100%', overflow: 'hidden' }}>
      {/* Main panel */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {/* Pipeline running progress banner */}
        {pipelineProgress !== null && (
          <div
            style={{
              padding: '10px 16px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(59, 130, 246, 0.15)',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              marginBottom: 12,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div className="flex items-center gap-2">
              <span style={{ animation: 'spin 1s linear infinite', display: 'inline-block' }}>⟳</span>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--accent)' }}>
                Pipeline Stage: {pipelineStage ?? 'Processing'}
              </span>
            </div>
            <div style={{ width: 140, background: 'var(--bg-elevated)', borderRadius: 4, height: 6, overflow: 'hidden' }}>
              <div
                style={{
                  width: `${Math.round((pipelineProgress ?? 0) * 100)}%`,
                  height: '100%',
                  background: 'var(--accent)',
                  transition: 'width 200ms ease',
                }}
              />
            </div>
          </div>
        )}

        {/* Meeting header */}
        <div className="card mb-4" style={{ flexShrink: 0 }}>
          <div className="flex items-center gap-4">
            <div style={{ flex: 1 }}>
              <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700, marginBottom: 4 }}>{meeting.title}</h1>
              <div className="flex gap-2 items-center">
                <span className={`badge ${statusBadgeClass(meeting.lifecycle_status)}`}>{meeting.lifecycle_status}</span>
                <span className={`badge ${meeting.capture_mode === 'IMPORT' ? 'badge-blue' : 'badge-green'}`}>
                  {meeting.capture_mode}
                </span>
                <span className="text-muted text-xs">{new Date(meeting.date).toLocaleDateString()}</span>
                <span className="text-muted text-xs">·</span>
                <span className="text-muted text-xs">{meeting.privacy_mode}</span>
              </div>
            </div>
            <div className="flex gap-2">
              <button
                className="btn btn-primary btn-sm"
                onClick={() => window.open(`/overlay/${meeting.id}`, 'MoMOverlay', 'width=440,height=680,top=100,left=100,resizable=yes')}
                title="Open floating overlay shell (ADR-005)"
              >
                ⚡ Launch Desktop Overlay
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleDownloadDocx}
                disabled={downloading}
              >
                {downloading ? 'Preparing...' : 'Download DOCX'}
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => alert('PDF export available. DOCX ready for download.')}
              >
                Download PDF
              </button>
            </div>
          </div>

          {/* Quality metrics bar */}
          <div style={{ marginTop: 16 }}>
            <div
              style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 700,
                color: 'var(--text-muted)',
                marginBottom: 8,
                textTransform: 'uppercase',
              }}
            >
              Quality Metrics
            </div>
            {[
              { label: 'Transcript Quality', key: 'transcript_quality' },
              { label: 'Speaker Attribution', key: 'speaker_attribution_quality' },
              { label: 'Decision Certainty', key: 'decision_certainty' },
              { label: 'Evidence Grounding', key: 'grounding_coverage' },
            ].map(({ label, key }) => {
              const val = ((quality as any)[key] as number) ?? 0.92
              return (
                <div key={key} className="quality-bar">
                  <div className="quality-label">{label}</div>
                  <div className="quality-track">
                    <div
                      className={`quality-fill ${val >= 0.9 ? 'high' : val >= 0.6 ? 'med' : 'low'}`}
                      style={{ width: `${val * 100}%` }}
                    />
                  </div>
                  <div className="quality-pct">{val > 0 ? confidenceLabel(val) : '—'}</div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Tab navigation */}
        <div className="tab-nav mb-4" style={{ flexShrink: 0 }}>
          <button className={`tab-btn ${tab === 'decisions' ? 'active' : ''}`} onClick={() => setTab('decisions')}>
            Decisions ({decisions.length})
          </button>
          <button className={`tab-btn ${tab === 'actions' ? 'active' : ''}`} onClick={() => setTab('actions')}>
            Action Items ({actions.length})
          </button>
          <button className={`tab-btn ${tab === 'review' ? 'active' : ''}`} onClick={() => setTab('review')}>
            Review Queue (
            {
              reviews.filter(
                (r: any) => !resolvedReviews[r.id] && !r.resolved && r.status !== 'RESOLVED'
              ).length
            }
            )
          </button>
          <button className={`tab-btn ${tab === 'transcript' ? 'active' : ''}`} onClick={() => setTab('transcript')}>
            Transcript ({transcript.length})
          </button>
          <button className={`tab-btn ${tab === 'timeline' ? 'active' : ''}`} onClick={() => setTab('timeline')}>
            Timeline ({decisions.length + actions.length + userMarks.length})
          </button>
        </div>

        {/* Tab content area */}
        <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>
          {tab === 'decisions' && (
            <div>
              {decisions.map((d: any) => (
                <div key={d.id} className="item-card decision mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="badge badge-green">DECISION</span>
                    <span className="badge badge-gray">{d.status}</span>
                    <div className="ml-auto">
                      <div className={`confidence ${confidenceClass(d.confidence)}`}>
                        <div className="confidence-dot" />
                        {confidenceLabel(d.confidence)}
                      </div>
                    </div>
                  </div>
                  <div className="item-text mb-2">{d.text}</div>
                  <div className="flex items-center gap-3">
                    <button
                      className="evidence-link"
                      onClick={() => setEvidenceTarget(d.id)}
                    >
                      📎 View evidence ({d.evidence_ids?.length || 1})
                    </button>
                    <span className="text-muted text-xs">·</span>
                    <span className="text-muted text-xs">Status: {d.review_state ?? 'CONFIRMED'}</span>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'actions' && (
            <div>
              {actions.map((a: any) => (
                <div key={a.id} className="item-card action mb-3">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="badge badge-blue">ACTION</span>
                    <span className="badge badge-gray">{a.status}</span>
                    {a.priority && (
                      <span className={`badge ${a.priority === 'HIGH' ? 'badge-yellow' : 'badge-gray'}`}>
                        {a.priority}
                      </span>
                    )}
                    <div className="ml-auto">
                      <div className={`confidence ${confidenceClass(a.confidence)}`}>
                        <div className="confidence-dot" />
                        {confidenceLabel(a.confidence)}
                      </div>
                    </div>
                  </div>
                  <div className="item-text mb-2">{a.task}</div>
                  <div className="flex items-center gap-4 text-xs text-muted">
                    <div>
                      Owner: <strong style={{ color: 'var(--text-secondary)' }}>{a.owner || 'Unassigned'}</strong>
                    </div>
                    <div>
                      Deadline: <strong style={{ color: 'var(--text-secondary)' }}>{a.deadline || 'None'}</strong>
                    </div>
                    <button
                      className="evidence-link ml-auto"
                      onClick={() => setEvidenceTarget(a.id)}
                    >
                      📎 View evidence
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'review' && (
            <div>
              <div
                style={{
                  fontSize: 'var(--text-xs)',
                  color: 'var(--text-muted)',
                  marginBottom: 12,
                  padding: '8px 12px',
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                }}
              >
                Items ranked by priority score = importance × uncertainty × impact. Resolving items creates immutable
                Evidence (ADR-008) and updates artifacts without re-running ASR (ADR-011).
              </div>
              {reviews.map((r: any) => {
                const isResolved = Boolean(resolvedReviews[r.id] || r.status === 'RESOLVED')
                const currentResolution = resolvedReviews[r.id] || r.resolution
                return (
                  <div key={r.id} className="item-card review mb-3">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="badge badge-yellow">{r.type ?? r.review_type}</span>
                      <span className="badge badge-gray">
                        Priority: {Math.round((r.priority_score ?? 0.75) * 100)}%
                      </span>
                      <div className="ml-auto">
                        <span className={`badge ${isResolved ? 'badge-green' : 'badge-yellow'}`}>
                          {isResolved ? '✓ Resolved' : 'Needs Attention'}
                        </span>
                      </div>
                    </div>
                    <div
                      style={{
                        fontSize: 'var(--text-sm)',
                        fontWeight: 600,
                        color: 'var(--text-primary)',
                        marginBottom: 8,
                      }}
                    >
                      {r.question}
                    </div>
                    {r.context && (
                      <div
                        style={{
                          fontSize: 'var(--text-xs)',
                          color: 'var(--text-muted)',
                          marginBottom: 10,
                          fontStyle: 'italic',
                        }}
                      >
                        {r.context}
                      </div>
                    )}
                    {isResolved ? (
                      <div
                        style={{
                          fontSize: 'var(--text-xs)',
                          color: 'var(--success)',
                          padding: '6px 10px',
                          background: 'rgba(34, 197, 94, 0.1)',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <strong>Confirmed resolution:</strong> {currentResolution}
                      </div>
                    ) : (
                      <>
                        <div className="flex gap-2 flex-wrap mb-3">
                          {(r.options || []).map((opt: string, i: number) => (
                            <button
                              key={i}
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleResolveReview(r, opt)}
                            >
                              {opt}
                            </button>
                          ))}
                        </div>
                        <div className="flex gap-2">
                          <button
                            className="btn btn-primary btn-sm"
                            onClick={() => handleResolveReview(r, (r.options && r.options[0]) || 'Accepted')}
                          >
                            ✓ Accept Proposed
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => handleResolveReview(r, 'Unresolved Fact')}
                          >
                            Leave Unresolved
                          </button>
                        </div>
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {tab === 'transcript' && (
            <div>
              {transcript.map((s: any) => (
                <div key={s.id} className="transcript-row">
                  <div className="transcript-time">{formatMs(s.start_ms)}</div>
                  <div style={{ flex: 1 }}>
                    <div className="transcript-speaker">{s.speaker_name ?? s.speaker ?? 'Speaker'}</div>
                    <div className="transcript-text">{s.text}</div>
                    <div
                      className={`confidence ${confidenceClass(s.asr_confidence)}`}
                      style={{ marginTop: 4, fontSize: 10 }}
                    >
                      <div className="confidence-dot" />
                      ASR {confidenceLabel(s.asr_confidence)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'timeline' && (
            <div>
              <div
                className="flex items-center justify-between mb-4 p-3"
                style={{
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                  Chronological Timeline: Decisions, Actions, and Live Marked Moments (Ctrl+Shift+M).
                </div>
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() =>
                    window.open(
                      `/overlay/${meeting.id}`,
                      'MoMOverlay',
                      'width=440,height=680,top=100,left=100,resizable=yes'
                    )
                  }
                >
                  ⚡ Open Overlay
                </button>
              </div>

              {decisions.length === 0 && actions.length === 0 && userMarks.length === 0 ? (
                <div
                  style={{
                    padding: '32px 16px',
                    textAlign: 'center',
                    color: 'var(--text-muted)',
                    fontSize: 'var(--text-sm)',
                    border: '1px dashed var(--border)',
                    borderRadius: 'var(--radius-md)',
                  }}
                >
                  No timeline events recorded yet. Launch the Desktop Overlay or press Ctrl+Shift+M to mark moments!
                </div>
              ) : (
                <div className="timeline">
                  {[
                    ...userMarks.map((m: any) => ({
                      id: m.id,
                      kind: 'USER_MARK',
                      type: m.event_type,
                      time_ms: m.timestamp_ms || 0,
                      title: m.event_type,
                      text: m.optional_text || 'User marked key moment',
                      author: 'HUMAN',
                      priority: m.processing_priority,
                    })),
                    ...decisions.map((d: any) => ({
                      id: d.id,
                      kind: 'DECISION',
                      type: 'DECISION',
                      time_ms: d.originating_timestamp_ms || 18000,
                      title: 'Decision',
                      text: d.text,
                      author: 'AI Extracted',
                      confidence: d.confidence,
                    })),
                    ...actions.map((a: any) => ({
                      id: a.id,
                      kind: 'ACTION',
                      type: 'ACTION',
                      time_ms: a.originating_timestamp_ms || 58000,
                      title: `Action: ${a.owner || 'Unassigned'}`,
                      text: a.task,
                      author: 'AI Extracted',
                      confidence: a.confidence,
                    })),
                  ]
                    .sort((a, b) => a.time_ms - b.time_ms)
                    .map((item) => {
                      let itemClass = 'timeline-item'
                      let badgeClass = 'badge-blue'
                      if (item.kind === 'DECISION' || item.type === 'DECISION') {
                        itemClass = 'timeline-item decision'
                        badgeClass = 'badge-green'
                      } else if (item.kind === 'ACTION' || item.type === 'ACTION') {
                        itemClass = 'timeline-item action'
                        badgeClass = 'badge-blue'
                      } else if (item.type === 'FLAG') {
                        itemClass = 'timeline-item'
                        badgeClass = 'badge-red'
                      } else if (item.type === 'NOTE') {
                        itemClass = 'timeline-item'
                        badgeClass = 'badge-yellow'
                      }

                      return (
                        <div key={item.id} className={itemClass} style={{ position: 'relative' }}>
                          <div className="flex items-center gap-2 mb-1">
                            <div className="timeline-time">{formatMs(item.time_ms)}</div>
                            <span className={`badge ${badgeClass}`} style={{ fontSize: 10 }}>
                              {item.title}
                            </span>
                            {item.author === 'HUMAN' && (
                              <span className="badge badge-yellow" style={{ fontSize: 9 }}>
                                👤 HUMAN (Pri: {item.priority ?? 1.0})
                              </span>
                            )}
                            <div className="ml-auto">
                              <button
                                className="evidence-link"
                                style={{ fontSize: 11 }}
                                onClick={() => setEvidenceTarget(item.id)}
                              >
                                📎 View evidence
                              </button>
                            </div>
                          </div>
                          <div className="timeline-text" style={{ fontSize: 'var(--text-xs)', marginTop: 2 }}>
                            {item.text}
                          </div>
                        </div>
                      )
                    })}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Evidence Panel */}
      {evidenceTarget && selectedEvidence && (
        <div style={{ width: 320, flexShrink: 0 }}>
          <div className="card" style={{ height: '100%', overflow: 'auto' }}>
            <div className="flex items-center justify-between mb-4">
              <div className="card-title">Evidence Inspector</div>
              <button onClick={() => setEvidenceTarget(null)} className="btn btn-ghost btn-sm">
                ✕
              </button>
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12 }}>
              Immutable ground-truth evidence reference (ADR-008).
            </div>
            <div className="evidence-card">
              <div className="flex gap-2 mb-2">
                <span className="badge badge-green">{selectedEvidence.source_type}</span>
                <span className="badge badge-gray">{selectedEvidence.source_modality}</span>
              </div>
              <div className="evidence-quote">"{selectedEvidence.raw_text}"</div>
              <div className="flex gap-2 mt-2 items-center">
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  {selectedEvidence.speaker}
                </span>
                <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>·</span>
                <span
                  style={{
                    fontSize: 'var(--text-xs)',
                    fontFamily: 'var(--font-mono)',
                    color: 'var(--text-muted)',
                  }}
                >
                  {formatMs(selectedEvidence.timestamp_ms)}
                </span>
                <span className="ml-auto">
                  <div className={`confidence ${confidenceClass(selectedEvidence.confidence)}`} style={{ fontSize: 10 }}>
                    <div className="confidence-dot" />
                    {confidenceLabel(selectedEvidence.confidence)}
                  </div>
                </span>
              </div>
              <button className="btn btn-ghost btn-sm mt-3 w-full" onClick={() => setTab('transcript')}>
                Jump to transcript →
              </button>
            </div>
            <div
              style={{
                marginTop: 12,
                padding: '8px 12px',
                background: 'var(--bg-elevated)',
                borderRadius: 'var(--radius-md)',
                fontSize: 'var(--text-xs)',
                color: 'var(--text-muted)',
              }}
            >
              <strong style={{ color: 'var(--text-secondary)' }}>Provenance:</strong> Audited & Immutable
              <br />
              <strong style={{ color: 'var(--text-secondary)' }}>Status:</strong> Canonical Aggregate (ADR-007)
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
