import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

interface UserMark {
  id: string
  meeting_id: string
  timestamp_ms: number
  event_type: string
  optional_text: string | null
  source: string
  processing_priority: number
  created_at: string
}

interface AudioStatus {
  state: string
  microphone_available: boolean
  system_audio_available: boolean
  degradation_reason: string | null
  fallback_applied: boolean
}

export default function Overlay() {
  const { id } = useParams<{ id?: string }>()
  const navigate = useNavigate()

  const [meetingId] = useState<string>(id || 'live-session')
  const [meetingTitle, setMeetingTitle] = useState<string>('Live Meeting Session')
  const [isCollapsed, setIsCollapsed] = useState<boolean>(false)
  const [audioStatus, setAudioStatus] = useState<AudioStatus>({
    state: 'MICROPHONE_ONLY',
    microphone_available: true,
    system_audio_available: false,
    degradation_reason: 'WASAPI system audio unavailable on current host',
    fallback_applied: true,
  })
  const [marks, setMarks] = useState<UserMark[]>([])
  const [noteText, setNoteText] = useState<string>('')
  const [selectedType, setSelectedType] = useState<string>('USER_MARK')
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false)
  const [elapsedSeconds, setElapsedSeconds] = useState<number>(0)
  const [toastMessage, setToastMessage] = useState<string | null>(null)

  // Timer
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedSeconds((prev) => prev + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  // Auto-dismiss toast
  useEffect(() => {
    if (toastMessage) {
      const t = setTimeout(() => setToastMessage(null), 3000)
      return () => clearTimeout(t)
    }
  }, [toastMessage])

  // Fetch meeting and session status
  useEffect(() => {
    async function initSession() {
      if (!meetingId) return
      try {
        // Fetch meeting details
        const mtgRes = await fetch(`http://localhost:8000/api/meetings/${meetingId}/record`)
        if (mtgRes.ok) {
          const rec = await mtgRes.json()
          if (rec.meeting?.title) setMeetingTitle(rec.meeting.title)
          if (rec.user_marks) setMarks(rec.user_marks)
        }

        // Fetch capture session status
        const sessRes = await fetch(`http://localhost:8000/api/capture/${meetingId}/session`)
        if (sessRes.ok) {
          const data = await sessRes.json()
          if (data.session?.audio_source_status) {
            setAudioStatus(data.session.audio_source_status)
          }
        } else {
          // If no session exists, auto-start one
          const startRes = await fetch('http://localhost:8000/api/capture/session/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ meeting_id: meetingId, capture_mode: 'OVERLAY' }),
          })
          if (startRes.ok) {
            const startData = await startRes.json()
            if (startData.audio_source_status) {
              setAudioStatus(startData.audio_source_status)
            }
          }
        }
      } catch (err) {
        console.warn('Backend offline, running overlay in local manual mode', err)
      }
    }

    initSession()

    // Setup WebSocket
    let ws: WebSocket | null = null
    try {
      ws = new WebSocket(`ws://localhost:8000/api/ws/overlay/${meetingId}`)
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'USER_MARK' && data.mark) {
            setMarks((prev) => {
              if (prev.some((m) => m.id === data.mark.id)) return prev
              return [data.mark, ...prev]
            })
          } else if (data.type === 'AUDIO_SOURCE_STATE_CHANGED' && data.audio_source_status) {
            setAudioStatus(data.audio_source_status)
          }
        } catch {}
      }
    } catch {}

    return () => {
      if (ws) ws.close()
    }
  }, [meetingId])

  // Mark Moment function
  const handleMarkMoment = async (eventType: string = selectedType, text: string = noteText) => {
    if (isSubmitting) return
    setIsSubmitting(true)

    const payload = {
      timestamp_ms: elapsedSeconds * 1000,
      event_type: eventType,
      text: text.trim() || undefined,
      priority: 1.0,
    }

    try {
      const res = await fetch(`http://localhost:8000/api/capture/${meetingId}/mark`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })

      if (res.ok) {
        const data = await res.json()
        if (data.mark) {
          setMarks((prev) => [data.mark, ...prev])
        }
        setToastMessage(`✓ Marked ${eventType} at ${formatSeconds(elapsedSeconds)}`)
        setNoteText('')
      } else {
        // Fallback local mark if backend errors
        const fallbackMark: UserMark = {
          id: `local-${Date.now()}`,
          meeting_id: meetingId,
          timestamp_ms: elapsedSeconds * 1000,
          event_type: eventType,
          optional_text: text.trim() || null,
          source: 'HUMAN',
          processing_priority: 1.0,
          created_at: new Date().toISOString(),
        }
        setMarks((prev) => [fallbackMark, ...prev])
        setToastMessage(`✓ Marked ${eventType} (offline)`)
        setNoteText('')
      }
    } catch {
      // Local fallback
      const fallbackMark: UserMark = {
        id: `local-${Date.now()}`,
        meeting_id: meetingId,
        timestamp_ms: elapsedSeconds * 1000,
        event_type: eventType,
        optional_text: text.trim() || null,
        source: 'HUMAN',
        processing_priority: 1.0,
        created_at: new Date().toISOString(),
      }
      setMarks((prev) => [fallbackMark, ...prev])
      setToastMessage(`✓ Marked ${eventType} (local fallback)`)
      setNoteText('')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Keyboard shortcut listener for Ctrl+Shift+M / Cmd+Shift+M
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toUpperCase() === 'M') {
        e.preventDefault()
        handleMarkMoment('USER_MARK', noteText)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [elapsedSeconds, noteText, selectedType])

  const formatSeconds = (totalSec: number) => {
    const m = Math.floor(totalSec / 60)
    const s = totalSec % 60
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  }

  const getAudioBadge = () => {
    switch (audioStatus.state) {
      case 'MICROPHONE_AND_SYS':
        return <span className="badge badge-green">● Mic + System Audio</span>
      case 'MICROPHONE_ONLY':
        return <span className="badge badge-yellow">● Mic Only</span>
      case 'SYSTEM_ONLY':
        return <span className="badge badge-yellow">● System Audio Only</span>
      case 'NO_AUDIO':
      default:
        return <span className="badge badge-red">● No Audio (Manual Mode)</span>
    }
  }

  // If collapsed to minimal floating pill
  if (isCollapsed) {
    return (
      <div
        style={{
          position: 'fixed',
          top: 16,
          right: 16,
          zIndex: 99999,
          background: 'rgba(20, 24, 33, 0.95)',
          backdropFilter: 'blur(16px)',
          border: '1px solid var(--border)',
          borderRadius: 24,
          padding: '8px 16px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6)',
          cursor: 'pointer',
        }}
        onClick={() => setIsCollapsed(false)}
      >
        <span style={{ color: 'var(--red)', animation: 'pulse 1.5s infinite', fontSize: 12 }}>●</span>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-primary)' }}>
          {formatSeconds(elapsedSeconds)}
        </span>
        <span className="badge badge-blue" style={{ fontSize: 10 }}>
          {marks.length} marks
        </span>
        <button
          className="btn btn-primary btn-sm"
          style={{ padding: '4px 10px', fontSize: 11, borderRadius: 12 }}
          onClick={(e) => {
            e.stopPropagation()
            handleMarkMoment('USER_MARK')
          }}
        >
          ⚡ Mark (Ctrl+Shift+M)
        </button>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>↗</span>
      </div>
    )
  }

  return (
    <div
      style={{
        width: '100%',
        maxWidth: 440,
        margin: '0 auto',
        minHeight: '100vh',
        background: 'var(--bg-canvas)',
        color: 'var(--text-primary)',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'Inter, sans-serif',
        boxSizing: 'border-box',
        padding: 16,
      }}
    >
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            position: 'fixed',
            top: 12,
            left: '50%',
            transform: 'translateX(-50%)',
            background: 'var(--accent)',
            color: '#fff',
            padding: '6px 16px',
            borderRadius: 20,
            fontSize: 'var(--text-xs)',
            fontWeight: 600,
            boxShadow: '0 4px 16px rgba(99, 102, 241, 0.5)',
            zIndex: 100000,
            animation: 'fadeIn 0.2s ease',
          }}
        >
          {toastMessage}
        </div>
      )}

      {/* Top Header Card */}
      <div
        className="card mb-3"
        style={{
          background: 'rgba(26, 31, 46, 0.95)',
          backdropFilter: 'blur(16px)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-lg)',
          padding: 14,
        }}
      >
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span style={{ color: 'var(--red)', fontSize: 12 }}>●</span>
            <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, letterSpacing: 0.5, color: 'var(--accent)' }}>
              OVERLAY CAPTURE
            </span>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              · {formatSeconds(elapsedSeconds)}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 11, padding: '2px 8px' }}
              onClick={() => setIsCollapsed(true)}
              title="Collapse to floating pill"
            >
              − Pill
            </button>
            <button
              className="btn btn-ghost btn-sm"
              style={{ fontSize: 11, padding: '2px 8px' }}
              onClick={() => navigate(`/meetings/${meetingId}`)}
              title="Open full workspace"
            >
              Workspace ↗
            </button>
          </div>
        </div>

        <h2 style={{ fontSize: 'var(--text-base)', fontWeight: 700, margin: '2px 0 6px 0' }}>
          {meetingTitle}
        </h2>

        <div className="flex items-center gap-2 flex-wrap">
          {getAudioBadge()}
          <span className="badge badge-gray">{marks.length} Moments Marked</span>
        </div>

        {/* Degradation Alert if Audio Failed */}
        {audioStatus.fallback_applied && (
          <div
            style={{
              marginTop: 10,
              padding: '6px 10px',
              borderRadius: 'var(--radius-md)',
              background: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              fontSize: 11,
              color: 'var(--text-secondary)',
              lineHeight: 1.4,
            }}
          >
            <strong>Note:</strong> {audioStatus.degradation_reason || 'Audio capture unavailable.'}
            <div style={{ color: 'var(--accent)', marginTop: 2 }}>
              Manual note-taking and Mark Moments remain fully operational (ADR-005).
            </div>
          </div>
        )}
      </div>

      {/* Main Action Hub: Mark Moment */}
      <div
        className="card mb-3"
        style={{
          padding: 16,
          background: 'rgba(30, 36, 53, 0.95)',
          border: '1px solid var(--accent)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: '0 4px 20px rgba(99, 102, 241, 0.15)',
        }}
      >
        <button
          className="btn btn-primary"
          style={{
            width: '100%',
            padding: '14px 16px',
            fontSize: 'var(--text-base)',
            fontWeight: 700,
            borderRadius: 'var(--radius-md)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
            boxShadow: '0 4px 16px rgba(99, 102, 241, 0.4)',
            marginBottom: 12,
          }}
          disabled={isSubmitting}
          onClick={() => handleMarkMoment('USER_MARK')}
        >
          <span style={{ fontSize: 18 }}>⚡</span>
          <span>Mark Moment</span>
          <span style={{ fontSize: 11, opacity: 0.8, fontWeight: 400, marginLeft: 4 }}>
            (Ctrl+Shift+M)
          </span>
        </button>

        {/* Category Specific Mark Buttons */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, marginBottom: 12 }}>
          <button
            className="btn btn-secondary btn-sm"
            style={{
              padding: '8px 4px',
              fontSize: 11,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              border: selectedType === 'DECISION' ? '1px solid var(--green)' : undefined,
            }}
            onClick={() => {
              setSelectedType('DECISION')
              handleMarkMoment('DECISION')
            }}
          >
            <span style={{ color: 'var(--green)', fontSize: 14 }}>✓</span>
            <span>Decision</span>
          </button>

          <button
            className="btn btn-secondary btn-sm"
            style={{
              padding: '8px 4px',
              fontSize: 11,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              border: selectedType === 'ACTION' ? '1px solid var(--accent)' : undefined,
            }}
            onClick={() => {
              setSelectedType('ACTION')
              handleMarkMoment('ACTION')
            }}
          >
            <span style={{ color: 'var(--accent)', fontSize: 14 }}>⚡</span>
            <span>Action</span>
          </button>

          <button
            className="btn btn-secondary btn-sm"
            style={{
              padding: '8px 4px',
              fontSize: 11,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              border: selectedType === 'NOTE' ? '1px solid var(--yellow)' : undefined,
            }}
            onClick={() => {
              setSelectedType('NOTE')
              handleMarkMoment('NOTE')
            }}
          >
            <span style={{ color: 'var(--yellow)', fontSize: 14 }}>📝</span>
            <span>Note</span>
          </button>

          <button
            className="btn btn-secondary btn-sm"
            style={{
              padding: '8px 4px',
              fontSize: 11,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 4,
              border: selectedType === 'FLAG' ? '1px solid var(--red)' : undefined,
            }}
            onClick={() => {
              setSelectedType('FLAG')
              handleMarkMoment('FLAG')
            }}
          >
            <span style={{ color: 'var(--red)', fontSize: 14 }}>🚩</span>
            <span>Flag</span>
          </button>
        </div>

        {/* Context Note Input */}
        <div className="flex gap-2">
          <input
            type="text"
            className="input"
            style={{
              flex: 1,
              fontSize: 'var(--text-xs)',
              padding: '8px 12px',
              background: 'var(--bg-canvas)',
              borderRadius: 'var(--radius-md)',
            }}
            placeholder="Add note or context (press Enter to mark)..."
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                handleMarkMoment('NOTE', noteText)
              }
            }}
          />
          <button
            className="btn btn-primary btn-sm"
            style={{ padding: '0 12px' }}
            disabled={!noteText.trim() || isSubmitting}
            onClick={() => handleMarkMoment('NOTE', noteText)}
          >
            Post
          </button>
        </div>
      </div>

      {/* Live Stream of Marked Moments */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div className="flex items-center justify-between mb-2">
          <span style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-muted)' }}>
            CAPTURED MOMENTS ({marks.length})
          </span>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Source: HUMAN (1.0 conf)</span>
        </div>

        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
          {marks.length === 0 ? (
            <div
              style={{
                padding: '24px 16px',
                textAlign: 'center',
                color: 'var(--text-muted)',
                fontSize: 'var(--text-xs)',
                border: '1px dashed var(--border)',
                borderRadius: 'var(--radius-md)',
              }}
            >
              No moments marked yet.
              <br />
              Click <strong>Mark Moment</strong> or press <strong>Ctrl+Shift+M</strong> during key discussion points.
            </div>
          ) : (
            marks.map((m) => {
              let badgeColor = 'badge-blue'
              if (m.event_type === 'DECISION') badgeColor = 'badge-green'
              if (m.event_type === 'FLAG') badgeColor = 'badge-red'
              if (m.event_type === 'NOTE') badgeColor = 'badge-yellow'

              return (
                <div
                  key={m.id}
                  style={{
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--bg-surface)',
                    border: '1px solid var(--border)',
                    fontSize: 'var(--text-xs)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 4,
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`badge ${badgeColor}`} style={{ fontSize: 10 }}>
                        {m.event_type}
                      </span>
                      <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>
                        {formatSeconds(Math.floor((m.timestamp_ms || 0) / 1000))}
                      </span>
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>Priority 1.0</span>
                  </div>
                  <div style={{ color: 'var(--text-primary)', marginTop: 2 }}>
                    {m.optional_text || 'Marked key moment'}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
