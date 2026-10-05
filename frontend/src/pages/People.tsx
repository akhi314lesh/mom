import { useState, useEffect } from 'react'

interface SpeakerItem {
  id: string
  label: string
  resolved: string | null
  confidence: number
  source: string
  speaking_pct: number
}

interface ParticipantItem {
  id: string
  name: string
  role: string
  email?: string
}

export default function People() {
  const [speakers, setSpeakers] = useState<SpeakerItem[]>([
    { id: 'spk-0', label: 'SPEAKER_0', resolved: 'Akhilesh', confidence: 0.95, source: 'HUMAN', speaking_pct: 38 },
    { id: 'spk-1', label: 'SPEAKER_1', resolved: 'Priya', confidence: 0.92, source: 'INFERRED', speaking_pct: 45 },
    { id: 'spk-2', label: 'SPEAKER_2', resolved: 'David', confidence: 0.88, source: 'INFERRED', speaking_pct: 17 },
  ])

  const [participants, setParticipants] = useState<ParticipantItem[]>([
    { id: 'p-1', name: 'Akhilesh', role: 'Tech Lead / Lead Architect' },
    { id: 'p-2', name: 'Priya', role: 'Data Architect / Schema Engineer' },
    { id: 'p-3', name: 'David', role: 'Product Manager' },
  ])

  const [identifyingSpk, setIdentifyingSpk] = useState<string | null>(null)
  const [inputName, setInputName] = useState('')
  const [inputRole, setInputRole] = useState('')

  useEffect(() => {
    fetch('http://localhost:8000/api/meetings/participants/all')
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => {
        if (data && data.length > 0) {
          setParticipants(data)
        }
      })
      .catch(() => {})
  }, [])

  const handleResolveSpeaker = (spkId: string, name: string) => {
    setSpeakers((prev) =>
      prev.map((s) =>
        s.id === spkId
          ? { ...s, resolved: name, confidence: 1.0, source: 'HUMAN' }
          : s
      )
    )
    setIdentifyingSpk(null)
    setInputName('')
    setInputRole('')
  }

  return (
    <div style={{ maxWidth: 880 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>People & Identity Resolution</h1>
        <p className="text-muted text-xs mt-2">
          Participant directory and speaker diarization attribution across meetings (Phase 3).
        </p>
      </div>

      {/* Directory stats */}
      <div className="grid-2 mb-6" style={{ gap: 16 }}>
        <div className="card">
          <div className="text-muted text-xs font-semibold uppercase mb-1">Total Participants</div>
          <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--accent)' }}>
            {participants.length}
          </div>
          <p className="text-muted text-xs mt-2">Organizational memory persistent entities</p>
        </div>
        <div className="card">
          <div className="text-muted text-xs font-semibold uppercase mb-1">Speaker Resolution Rate</div>
          <div style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--success)' }}>
            100%
          </div>
          <p className="text-muted text-xs mt-2">All diarized labels attributed to verified people</p>
        </div>
      </div>

      {/* Speaker Diarization Attribution */}
      <div className="card mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="card-title">Diarized Speaker Labels</div>
            <div className="text-muted text-xs mt-1">
              Speakers detected by acoustic diarization (pyannote.audio) and mapped to known participants.
            </div>
          </div>
        </div>

        {speakers.map((s) => (
          <div
            key={s.id}
            style={{
              padding: '14px 0',
              borderBottom: '1px solid var(--border-subtle)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
              <div
                style={{
                  width: 42,
                  height: 42,
                  borderRadius: '50%',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 16,
                  color: 'var(--accent)',
                  flexShrink: 0,
                }}
              >
                ◎
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                  <span style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                    {s.resolved ?? `${s.label} (unresolved)`}
                  </span>
                  <span className="badge badge-gray" style={{ fontSize: 10 }}>
                    {s.label}
                  </span>
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                  {s.speaking_pct}% speaking time · Source: {s.source} · Confidence: {Math.round(s.confidence * 100)}%
                </div>
              </div>

              {s.source === 'HUMAN' ? (
                <span className="badge badge-green">✓ Verified by User</span>
              ) : (
                <span className="badge badge-yellow">Inferred</span>
              )}

              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setIdentifyingSpk(identifyingSpk === s.id ? null : s.id)}
              >
                {identifyingSpk === s.id ? 'Cancel' : 'Reassign →'}
              </button>
            </div>

            {/* Inline identification popup */}
            {identifyingSpk === s.id && (
              <div
                style={{
                  marginTop: 12,
                  padding: 14,
                  borderRadius: 'var(--radius-md)',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                }}
              >
                <div style={{ fontSize: 'var(--text-xs)', fontWeight: 600, marginBottom: 8, color: 'var(--text-primary)' }}>
                  Map {s.label} to a participant:
                </div>
                <div className="flex gap-2 flex-wrap mb-3">
                  {participants.map((p) => (
                    <button
                      key={p.id}
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleResolveSpeaker(s.id, p.name)}
                    >
                      {p.name} ({p.role})
                    </button>
                  ))}
                </div>
                <div className="flex gap-2 items-center">
                  <input
                    value={inputName}
                    onChange={(e) => setInputName(e.target.value)}
                    placeholder="Or enter new name..."
                    style={{
                      flex: 1,
                      padding: '6px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border)',
                      color: 'var(--text-primary)',
                      fontSize: 'var(--text-xs)',
                    }}
                  />
                  <input
                    value={inputRole}
                    onChange={(e) => setInputRole(e.target.value)}
                    placeholder="Role (optional)"
                    style={{
                      flex: 1,
                      padding: '6px 10px',
                      borderRadius: 'var(--radius-sm)',
                      background: 'var(--bg-card)',
                      border: '1px solid var(--border)',
                      color: 'var(--text-primary)',
                      fontSize: 'var(--text-xs)',
                    }}
                  />
                  <button
                    className="btn btn-primary btn-sm"
                    disabled={!inputName.trim()}
                    onClick={() => handleResolveSpeaker(s.id, inputName.trim())}
                  >
                    Confirm
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Participants Directory */}
      <div className="card">
        <div className="card-title mb-4">Organizational Participants Directory</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {participants.map((p) => (
            <div
              key={p.id}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 'var(--text-sm)', color: 'var(--text-primary)' }}>
                  {p.name}
                </div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{p.role}</div>
              </div>
              <span className="badge badge-blue">Team Member</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
