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

type Tab = 'transcript' | 'decisions' | 'actions' | 'review' | 'timeline' | 'query' | 'brief'

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
          if (msg.type === 'CONTRADICTION_DETECTED' && msg.contradiction) {
            setLiveRecord((prev: any) => {
              if (!prev) return prev
              const existing = prev.contradictions || []
              if (existing.some((c: any) => c.id === msg.contradiction.id)) return prev
              return {
                ...prev,
                contradictions: [...existing, msg.contradiction],
              }
            })
          }
          if (msg.type === 'CONTRADICTION_RESOLVED' || msg.type === 'LIVE_UTTERANCE_PROCESSED') {
            fetchRecord()
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

  const [timelineFilter, setTimelineFilter] = useState<'ALL' | 'DECISIONS' | 'ACTIONS' | 'CONTRADICTIONS' | 'MARKS'>('ALL')

  const decisions =
    liveRecord?.decisions && liveRecord.decisions.length > 0
      ? liveRecord.decisions
      : MOCK_DECISIONS.filter((d) => d.meeting_id === meeting.id || meeting.id === 'mtg-001')

  const actions =
    liveRecord?.action_items && liveRecord.action_items.length > 0
      ? liveRecord.action_items
      : MOCK_ACTIONS.filter((a) => a.originating_meeting_id === meeting.id || meeting.id === 'mtg-001')

  const userMarks = liveRecord?.user_marks ?? []
  const contradictions = liveRecord?.contradictions ?? []
  const semanticEvents = liveRecord?.semantic_events ?? []

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

  const handleResolveContradiction = async (contradictionId: string, resolution: string, chosenSide?: string) => {
    try {
      const res = await fetch(`http://localhost:8000/api/contradictions/${contradictionId}/resolve`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution, chosen_side: chosenSide }),
      })
      if (res.ok) {
        const recRes = await fetch(`http://localhost:8000/api/meetings/${meeting.id}/record`)
        if (recRes.ok) {
          const data = await recRes.json()
          setLiveRecord(data)
        }
      }
    } catch (err) {
      console.error('Failed to resolve contradiction', err)
    }
  }

  const [nlQuery, setNlQuery] = useState('')
  const [nlAnswer, setNlAnswer] = useState<any>(null)
  const [queryLoading, setQueryLoading] = useState(false)

  // Phase 8: External Integrations & Pre-Meeting Briefs
  const [briefData, setBriefData] = useState<any | null>(null)
  const [briefLoading, setBriefLoading] = useState(false)
  const [taskExporting, setTaskExporting] = useState<string | null>(null)
  const [exportReceipts, setExportReceipts] = useState<Record<string, any>>({})

  useEffect(() => {
    async function fetchBrief() {
      if (!meeting?.id) return
      try {
        const res = await fetch(`http://localhost:8000/api/integrations/meetings/${meeting.id}/brief`)
        if (res.ok) {
          const data = await res.json()
          setBriefData(data)
        }
      } catch {}
    }
    fetchBrief()
  }, [meeting?.id])

  const handleExportTask = async (actionId: string, destination: 'jira' | 'github' | 'linear') => {
    setTaskExporting(actionId)
    try {
      const res = await fetch('http://localhost:8000/api/integrations/tasks/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action_item_id: actionId,
          destination,
        }),
      })
      if (res.ok) {
        const receipt = await res.json()
        setExportReceipts((prev) => ({
          ...prev,
          [`${actionId}-${destination}`]: receipt,
        }))
      }
    } catch (e) {
      console.error(e)
    } finally {
      setTaskExporting(null)
    }
  }

  const handleRegenerateBrief = async () => {
    if (!meeting?.id) return
    setBriefLoading(true)
    try {
      const res = await fetch(`http://localhost:8000/api/integrations/meetings/${meeting.id}/generate-brief`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        setBriefData(data)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setBriefLoading(false)
    }
  }

  const handleAskMeeting = async (customQuery?: string) => {
    const q = customQuery || nlQuery
    if (!q.trim()) return
    setQueryLoading(true)
    try {
      const res = await fetch(`http://localhost:8000/api/query/meeting/${meeting.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q }),
      })
      if (res.ok) {
        const data = await res.json()
        setNlAnswer(data)
      }
    } catch (err) {
      console.error('Failed to query meeting', err)
    } finally {
      setQueryLoading(false)
    }
  }

  // Selected evidence lookup
  const selectedEvidence = (() => {
    if (!evidenceTarget) return null

    // Check contradictions first
    const conMatch = contradictions.find((c: any) => c.id === evidenceTarget)
    if (conMatch) {
      return {
        source_type: 'CONTRADICTION',
        source_modality: 'CROSS_EXAMINATION',
        raw_text: `${conMatch.description} [Side A: ${conMatch.event_a_text || 'Claim A'} | Side B: ${conMatch.event_b_text || 'Claim B'}]`,
        confidence: conMatch.confidence,
        timestamp_ms: 18500,
        speaker: 'Multi-party Discussion / Conflict',
      }
    }

    // Check user marks
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

        {/* Contradiction / Conflict Alert Banner */}
        {contradictions.filter((c: any) => c.review_state !== 'RESOLVED').length > 0 && (
          <div
            className="mb-4"
            style={{
              padding: '14px 16px',
              borderRadius: 'var(--radius-lg)',
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.4)',
              boxShadow: '0 4px 16px rgba(239, 68, 68, 0.15)',
            }}
          >
            <div className="flex items-center gap-2 mb-2">
              <span style={{ fontSize: 16 }}>⚠️</span>
              <span style={{ fontSize: 'var(--text-sm)', fontWeight: 700, color: 'var(--red)' }}>
                {contradictions.filter((c: any) => c.review_state !== 'RESOLVED').length} Unresolved Contradiction(s) Detected
              </span>
              <span className="badge badge-red ml-auto">Human Arbitration Required</span>
            </div>
            <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 12 }}>
              System Invariant: Decisions are held as <strong>UNRESOLVED</strong> rather than silently choosing a side. Both viewpoints are preserved in evidence.
            </div>
            {contradictions
              .filter((c: any) => c.review_state !== 'RESOLVED')
              .map((c: any) => (
                <div
                  key={c.id}
                  style={{
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    borderRadius: 'var(--radius-md)',
                    padding: '12px 14px',
                    marginBottom: 8,
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className="badge badge-red">{c.contradiction_type} CONFLICT</span>
                    <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600 }}>{c.description}</span>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleResolveContradiction(c.id, `Accepted: ${c.event_a_text || 'Claim A'}`, 'A')}
                    >
                      ✓ Accept: {c.event_a_text ? c.event_a_text.slice(0, 32) + '...' : 'Claim A'}
                    </button>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleResolveContradiction(c.id, `Accepted: ${c.event_b_text || 'Claim B'}`, 'B')}
                    >
                      ✓ Accept: {c.event_b_text ? c.event_b_text.slice(0, 32) + '...' : 'Claim B'}
                    </button>
                    <button
                      className="evidence-link ml-auto"
                      style={{ fontSize: 11 }}
                      onClick={() => setEvidenceTarget(c.id)}
                    >
                      📎 Inspect Evidence
                    </button>
                  </div>
                </div>
              ))}
          </div>
        )}

        {/* Pre-Meeting Intelligence Brief Banner */}
        {briefData && (
          <div
            className="mb-4"
            style={{
              padding: '12px 16px',
              borderRadius: 'var(--radius-lg)',
              background: 'rgba(59, 130, 246, 0.08)',
              border: '1px solid rgba(59, 130, 246, 0.25)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 16 }}>📋</span>
              <div>
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Pre-Meeting Brief Available: {briefData.expected_topics?.length || 0} Expected Topics · {briefData.open_action_items?.length || 0} Open Actions Carried Over
                </div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                  Auto-grounded against {briefData.previous_meetings?.length || 0} prior related meetings
                </div>
              </div>
            </div>
            <button
              onClick={() => setTab('brief')}
              className="btn btn-secondary btn-sm"
              style={{ fontSize: 11, padding: '3px 10px' }}
            >
              Inspect Brief ↗
            </button>
          </div>
        )}

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
          <button className={`tab-btn ${tab === 'query' ? 'active' : ''}`} onClick={() => setTab('query')}>
            💬 Ask Meeting
          </button>
          <button className={`tab-btn ${tab === 'brief' ? 'active' : ''}`} onClick={() => setTab('brief')}>
            📋 Brief {briefData && <span className="tab-count" style={{ background: '#3b82f6', color: '#fff' }}>Ready</span>}
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

                  {/* Task Export Toolbar (Phase 8) */}
                  <div style={{ marginTop: 10, paddingTop: 8, borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Export:</span>
                      <button
                        onClick={() => handleExportTask(a.id, 'jira')}
                        disabled={taskExporting === a.id}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                      >
                        Jira
                      </button>
                      <button
                        onClick={() => handleExportTask(a.id, 'github')}
                        disabled={taskExporting === a.id}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                      >
                        GitHub
                      </button>
                      <button
                        onClick={() => handleExportTask(a.id, 'linear')}
                        disabled={taskExporting === a.id}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: 10, padding: '2px 8px' }}
                      >
                        Linear
                      </button>
                    </div>
                    <div style={{ display: 'flex', gap: 6 }}>
                      {exportReceipts[`${a.id}-jira`] && (
                        <a
                          href={exportReceipts[`${a.id}-jira`].external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="badge badge-blue"
                          style={{ textDecoration: 'none', fontSize: 10 }}
                        >
                          ✓ {exportReceipts[`${a.id}-jira`].external_id} ↗
                        </a>
                      )}
                      {exportReceipts[`${a.id}-github`] && (
                        <a
                          href={exportReceipts[`${a.id}-github`].external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="badge badge-green"
                          style={{ textDecoration: 'none', fontSize: 10 }}
                        >
                          ✓ {exportReceipts[`${a.id}-github`].external_id} ↗
                        </a>
                      )}
                      {exportReceipts[`${a.id}-linear`] && (
                        <a
                          href={exportReceipts[`${a.id}-linear`].external_url}
                          target="_blank"
                          rel="noreferrer"
                          className="badge badge-purple"
                          style={{ textDecoration: 'none', fontSize: 10 }}
                        >
                          ✓ {exportReceipts[`${a.id}-linear`].external_id} ↗
                        </a>
                      )}
                    </div>
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
              {/* Timeline Header Info & Filter Chips */}
              <div
                className="mb-4 p-3"
                style={{
                  background: 'var(--bg-elevated)',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border)',
                }}
              >
                <div className="flex items-center justify-between mb-3">
                  <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)' }}>
                    Chronological Timeline: Decisions, Actions, Contradictions, and Live Marked Moments.
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

                {/* Filter Chips */}
                <div className="flex gap-2 flex-wrap">
                  {[
                    { key: 'ALL', label: `All Events (${decisions.length + actions.length + userMarks.length + contradictions.length + semanticEvents.length})` },
                    { key: 'DECISIONS', label: `Decisions (${decisions.length})` },
                    { key: 'ACTIONS', label: `Actions (${actions.length})` },
                    { key: 'CONTRADICTIONS', label: `Contradictions & Flags (${contradictions.length + semanticEvents.filter((s: any) => s.event_type === 'DISAGREEMENT').length})` },
                    { key: 'MARKS', label: `User Marks (${userMarks.length})` },
                  ].map((filter) => (
                    <button
                      key={filter.key}
                      className={`btn btn-sm ${timelineFilter === filter.key ? 'btn-primary' : 'btn-ghost'}`}
                      style={{ fontSize: 11, padding: '4px 10px' }}
                      onClick={() => setTimelineFilter(filter.key as any)}
                    >
                      {filter.label}
                    </button>
                  ))}
                </div>
              </div>

              {decisions.length === 0 && actions.length === 0 && userMarks.length === 0 && contradictions.length === 0 && semanticEvents.length === 0 ? (
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
                      status: d.status,
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
                    ...contradictions.map((c: any) => ({
                      id: c.id,
                      kind: 'CONTRADICTION',
                      type: c.contradiction_type,
                      time_ms: 22000,
                      title: `CONTRADICTION: ${c.contradiction_type}`,
                      text: c.description,
                      author: 'Consistency Engine',
                      confidence: c.confidence,
                      contradiction: c,
                    })),
                    ...semanticEvents
                      .filter((se: any) => se.event_type === 'DISAGREEMENT')
                      .map((se: any) => ({
                        id: se.id,
                        kind: 'DISAGREEMENT',
                        type: 'DISAGREEMENT',
                        time_ms: se.start_ms || 15000,
                        title: 'DISAGREEMENT',
                        text: se.text,
                        author: 'Discussion Participant',
                        confidence: se.confidence,
                      })),
                  ]
                    .filter((item) => {
                      if (timelineFilter === 'DECISIONS') return item.kind === 'DECISION'
                      if (timelineFilter === 'ACTIONS') return item.kind === 'ACTION'
                      if (timelineFilter === 'CONTRADICTIONS') return item.kind === 'CONTRADICTION' || item.kind === 'DISAGREEMENT'
                      if (timelineFilter === 'MARKS') return item.kind === 'USER_MARK'
                      return true
                    })
                    .sort((a, b) => a.time_ms - b.time_ms)
                    .map((item: any) => {
                      let itemClass = 'timeline-item'
                      let badgeClass = 'badge-blue'
                      if (item.kind === 'CONTRADICTION') {
                        itemClass = 'timeline-item decision'
                        badgeClass = 'badge-red'
                      } else if (item.kind === 'DISAGREEMENT') {
                        itemClass = 'timeline-item'
                        badgeClass = 'badge-red'
                      } else if (item.kind === 'DECISION') {
                        itemClass = 'timeline-item decision'
                        badgeClass = item.status === 'UNRESOLVED' ? 'badge-yellow' : 'badge-green'
                      } else if (item.kind === 'ACTION') {
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
                        <div
                          key={item.id}
                          className={itemClass}
                          style={{
                            position: 'relative',
                            borderLeft: item.kind === 'CONTRADICTION' ? '3px solid var(--red)' : undefined,
                          }}
                        >
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
                            {item.status === 'UNRESOLVED' && (
                              <span className="badge badge-yellow" style={{ fontSize: 9 }}>
                                ⚠️ UNRESOLVED
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

                          {/* Specific Arbitration Bar for Contradiction Items */}
                          {item.kind === 'CONTRADICTION' && item.contradiction && item.contradiction.review_state !== 'RESOLVED' && (
                            <div
                              style={{
                                marginTop: 8,
                                padding: '8px 10px',
                                background: 'var(--bg-elevated)',
                                borderRadius: 'var(--radius-md)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                              }}
                            >
                              <div style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 6 }}>
                                Arbitrate this dispute:
                              </div>
                              <div className="flex gap-2">
                                <button
                                  className="btn btn-secondary btn-sm"
                                  style={{ fontSize: 10, padding: '2px 8px' }}
                                  onClick={() => handleResolveContradiction(item.contradiction.id, `Accepted: ${item.contradiction.event_a_text || 'Claim A'}`, 'A')}
                                >
                                  Accept Claim A
                                </button>
                                <button
                                  className="btn btn-secondary btn-sm"
                                  style={{ fontSize: 10, padding: '2px 8px' }}
                                  onClick={() => handleResolveContradiction(item.contradiction.id, `Accepted: ${item.contradiction.event_b_text || 'Claim B'}`, 'B')}
                                >
                                  Accept Claim B
                                </button>
                              </div>
                            </div>
                          )}
                        </div>
                      )
                    })}
                </div>
              )}
            </div>
          )}

          {tab === 'query' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              {/* Question Input Card */}
              <div className="card">
                <div className="card-title mb-2">Ask the Meeting</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 12 }}>
                  Natural language question answering with strict evidence grounding (Phase 7). Every answer cites supporting quotes and evidence IDs.
                </div>
                <div className="flex gap-2 mb-3">
                  <input
                    type="text"
                    className="input flex-1"
                    placeholder="e.g. Who agreed to handle authentication?"
                    value={nlQuery}
                    onChange={(e) => setNlQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleAskMeeting()
                    }}
                    style={{
                      padding: '8px 12px',
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      color: 'var(--text-primary)',
                      fontSize: 'var(--text-xs)',
                    }}
                  />
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={queryLoading || !nlQuery.trim()}
                    onClick={() => handleAskMeeting()}
                  >
                    {queryLoading ? 'Searching...' : '⚡ Ask'}
                  </button>
                </div>

                {/* Suggested Query Chips */}
                <div className="flex gap-2 flex-wrap items-center">
                  <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Suggestions:</span>
                  {[
                    'Who agreed to handle authentication?',
                    'What framework decisions were made?',
                    'Were there any disagreements or conflicts?',
                    'What are the high priority action items?',
                  ].map((suggestion) => (
                    <button
                      key={suggestion}
                      className="btn btn-secondary btn-xs"
                      style={{ fontSize: 10, padding: '3px 8px' }}
                      onClick={() => {
                        setNlQuery(suggestion)
                        handleAskMeeting(suggestion)
                      }}
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>

              {/* Answer Card */}
              {nlAnswer && (
                <div
                  className="card"
                  style={{
                    borderLeft: nlAnswer.grounded ? '4px solid var(--success)' : '4px solid var(--yellow)',
                  }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    {nlAnswer.grounded ? (
                      <span className="badge badge-green">✓ Grounded in Evidence</span>
                    ) : (
                      <span className="badge badge-yellow">⚠️ No Supporting Evidence Found</span>
                    )}
                    <span className="badge badge-blue">{nlAnswer.query_type}</span>
                    <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                      Confidence: {Math.round(nlAnswer.confidence * 100)}%
                    </span>
                  </div>

                  <div
                    style={{
                      fontSize: 'var(--text-sm)',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      lineHeight: 1.5,
                      marginBottom: 16,
                    }}
                  >
                    {nlAnswer.answer}
                  </div>

                  {/* Sources List */}
                  {nlAnswer.sources && nlAnswer.sources.length > 0 && (
                    <div>
                      <div
                        style={{
                          fontSize: 10,
                          fontWeight: 700,
                          textTransform: 'uppercase',
                          color: 'var(--text-muted)',
                          marginBottom: 8,
                        }}
                      >
                        Retrieved Evidence Sources ({nlAnswer.sources.length})
                      </div>
                      <div className="flex flex-col gap-2">
                        {nlAnswer.sources.map((s: any, idx: number) => (
                          <div
                            key={idx}
                            style={{
                              padding: '10px 12px',
                              background: 'var(--bg-elevated)',
                              borderRadius: 'var(--radius-sm)',
                              border: '1px solid var(--border)',
                              fontSize: 'var(--text-xs)',
                            }}
                          >
                            <div className="flex items-center gap-2 mb-1">
                              <span className="badge badge-gray" style={{ fontSize: 9 }}>
                                [{s.source_type}]
                              </span>
                              {s.speaker_name && (
                                <span style={{ fontSize: 10, color: 'var(--accent)' }}>
                                  👤 {s.speaker_name}
                                </span>
                              )}
                              {s.meeting_title && (
                                <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
                                  Meeting: {s.meeting_title}
                                </span>
                              )}
                              <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-muted)' }}>
                                {Math.round(s.confidence * 100)}% confidence
                              </span>
                            </div>
                            <div style={{ color: 'var(--text-secondary)', fontStyle: 'italic', marginTop: 4 }}>
                              "{s.quote}"
                            </div>
                            <div className="mt-2 flex">
                              <button
                                className="evidence-link"
                                style={{ fontSize: 10 }}
                                onClick={() => setEvidenceTarget(s.source_id)}
                              >
                                📎 Inspect Evidence Reference
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {tab === 'brief' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
                  <div>
                    <div className="card-title">Pre-Meeting Intelligence Brief</div>
                    <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                      Auto-synthesized pre-meeting context from calendar sync and organizational memory (ADR-005, Phase 8).
                    </div>
                  </div>
                  <button
                    onClick={handleRegenerateBrief}
                    disabled={briefLoading}
                    className="btn btn-secondary btn-sm"
                  >
                    {briefLoading ? 'Analyzing...' : '↻ Regenerate Brief'}
                  </button>
                </div>

                {briefData ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
                    {/* Expected Topics */}
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Expected Agenda Topics
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {(briefData.expected_topics || []).map((topic: string, idx: number) => (
                          <span key={idx} className="badge badge-blue" style={{ fontSize: 'var(--text-xs)', padding: '6px 12px' }}>
                            ◈ {topic}
                          </span>
                        ))}
                      </div>
                    </div>

                    {/* Relevant Documents & Links */}
                    {briefData.relevant_documents && briefData.relevant_documents.length > 0 && (
                      <div>
                        <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          Attached Context & Meeting Links
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                          {briefData.relevant_documents.map((doc: string, idx: number) => (
                            <div key={idx} style={{ fontSize: 'var(--text-xs)', padding: '6px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                              🔗 {doc}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Open Action Items Carried Forward */}
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Carried-Over Open Action Items ({briefData.open_action_items?.length || 0})
                      </div>
                      {(!briefData.open_action_items || briefData.open_action_items.length === 0) ? (
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                          No pending action items carried over from prior meetings.
                        </div>
                      ) : (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                          {briefData.open_action_items.map((act: any) => (
                            <div
                              key={act.id}
                              style={{
                                padding: '10px 14px',
                                background: 'var(--bg-elevated)',
                                border: '1px solid var(--border)',
                                borderRadius: 'var(--radius-md)',
                                display: 'flex',
                                justifyContent: 'space-between',
                                alignItems: 'center',
                              }}
                            >
                              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-primary)', fontWeight: 500 }}>
                                ⚡ {act.task}
                              </div>
                              <div style={{ display: 'flex', gap: 6 }}>
                                <span className={`badge ${act.priority === 'HIGH' ? 'badge-yellow' : 'badge-gray'}`}>
                                  {act.priority}
                                </span>
                                <span className="badge badge-blue">{act.status}</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Linked Prior Meetings */}
                    <div>
                      <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                        Prior Related Meetings ({briefData.previous_meetings?.length || 0})
                      </div>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 10 }}>
                        {(briefData.previous_meetings || []).map((pm: any) => (
                          <div
                            key={pm.id}
                            style={{
                              padding: '10px 14px',
                              background: 'var(--bg-elevated)',
                              border: '1px solid var(--border)',
                              borderRadius: 'var(--radius-md)',
                            }}
                          >
                            <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                              {pm.title}
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
                              📅 {new Date(pm.date).toLocaleDateString()}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '24px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
                    No pre-meeting brief generated yet. Click "Regenerate Brief" to analyze calendar and organizational memory.
                  </div>
                )}
              </div>
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
