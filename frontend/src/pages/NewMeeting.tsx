import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

const CAPTURE_MODES = [
  { value: 'IMPORT', label: 'Import File', desc: 'Upload an audio or video recording', icon: '⬆', available: ['Audio', 'Timestamps', 'Imported Transcript'], unavailable: ['Live Capture', 'Manual Marks', 'Overlay'] },
  { value: 'RECORDING', label: 'Record Meeting', desc: 'Capture microphone and/or system audio', icon: '⏺', available: ['Microphone', 'System Audio (WASAPI)', 'Timestamps'], unavailable: ['Manual Marks (use Overlay mode)'] },
  { value: 'OVERLAY', label: 'Live Overlay', desc: 'Always-on-top capture with manual event marking', icon: '◉', available: ['Microphone', 'System Audio (WASAPI)', 'Manual Marks', 'Timestamps', 'User Marks (Ctrl+Shift+M)'], unavailable: [] },
  { value: 'NOTES_ONLY', label: 'Notes Only', desc: 'Manual structured input — no audio', icon: '✎', available: ['Manual Text Input', 'Structured Events'], unavailable: ['Audio', 'Timestamps', 'Speaker Attribution'] },
]

export default function NewMeeting() {
  const navigate = useNavigate()
  const [mode, setMode] = useState('IMPORT')
  const [title, setTitle] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [privacy, setPrivacy] = useState('LOCAL')

  const selected = CAPTURE_MODES.find(m => m.value === mode)!

  const handleCreate = () => {
    // Phase 0: navigate to mock meeting
    navigate('/meetings/mtg-001')
  }

  return (
    <div style={{ maxWidth: 760 }}>
      <div className="mb-6">
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 700 }}>New Meeting</h1>
        <p className="text-muted text-xs mt-2">Select a capture mode and configure your meeting.</p>
      </div>

      {/* Title */}
      <div className="card mb-4">
        <div className="card-title mb-4">Meeting Details</div>
        <div style={{ marginBottom: 16 }}>
          <label style={{ display: 'block', fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>
            Title
          </label>
          <input
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="e.g. Backend Architecture Review"
            style={{
              width: '100%', padding: '10px 14px', borderRadius: 'var(--radius-md)',
              background: 'var(--bg-elevated)', border: '1px solid var(--border)',
              color: 'var(--text-primary)', fontSize: 'var(--text-sm)', outline: 'none',
              fontFamily: 'var(--font-sans)',
            }}
          />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase' }}>
            Privacy Mode
          </label>
          <div className="flex gap-2">
            {['LOCAL', 'CLOUD', 'HYBRID'].map(p => (
              <button key={p} onClick={() => setPrivacy(p)}
                className={`btn btn-sm ${privacy === p ? 'btn-primary' : 'btn-secondary'}`}>
                {p === 'LOCAL' ? '🔒 Local' : p === 'CLOUD' ? '☁ Cloud' : '⚡ Hybrid'}
              </button>
            ))}
          </div>
          <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: 6 }}>
            {privacy === 'LOCAL' ? 'All processing stays on this machine. No data sent externally.' : privacy === 'CLOUD' ? 'Audio and transcript may be sent to cloud providers.' : 'Local ASR, cloud LLM. Transcript stays local.'}
          </p>
        </div>
      </div>

      {/* Capture Mode */}
      <div className="card mb-4">
        <div className="card-title mb-4">Capture Mode</div>
        <div className="grid-2 mb-4" style={{ gap: 8 }}>
          {CAPTURE_MODES.map(m => (
            <div key={m.value}
              onClick={() => setMode(m.value)}
              style={{
                padding: '16px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
                border: `2px solid ${mode === m.value ? 'var(--accent)' : 'var(--border)'}`,
                background: mode === m.value ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                transition: 'all 150ms',
              }}>
              <div style={{ fontSize: 20, marginBottom: 6 }}>{m.icon}</div>
              <div style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 3 }}>{m.label}</div>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{m.desc}</div>
            </div>
          ))}
        </div>

        {/* Evidence manifest preview */}
        <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: 12 }}>
          <div style={{ fontSize: 'var(--text-xs)', fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase' }}>
            Evidence Manifest for {selected.label}
          </div>
          <div className="flex gap-4">
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 'var(--text-xs)', color: 'var(--success)', fontWeight: 600, marginBottom: 4 }}>✓ Available</div>
              {selected.available.map(a => <div key={a} style={{ fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', marginBottom: 2 }}>• {a}</div>)}
            </div>
            {selected.unavailable.length > 0 && (
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--error)', fontWeight: 600, marginBottom: 4 }}>✗ Unavailable</div>
                {selected.unavailable.map(a => <div key={a} style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 2 }}>• {a}</div>)}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* File upload for IMPORT mode */}
      {mode === 'IMPORT' && (
        <div className="card mb-4">
          <div className="card-title mb-4">Upload File</div>
          <div style={{ border: '2px dashed var(--border)', borderRadius: 'var(--radius-md)', padding: '32px', textAlign: 'center' }}>
            <div style={{ fontSize: 32, marginBottom: 8 }}>⬆</div>
            <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginBottom: 4 }}>
              Drop audio/video file here or
            </div>
            <label style={{ color: 'var(--accent)', cursor: 'pointer', fontSize: 'var(--text-sm)', fontWeight: 500 }}>
              browse files
              <input type="file" accept=".mp3,.wav,.m4a,.ogg,.flac,.webm,.mp4" style={{ display: 'none' }}
                onChange={e => setFile(e.target.files?.[0] ?? null)} />
            </label>
            {file && <div style={{ marginTop: 8, fontSize: 'var(--text-xs)', color: 'var(--success)' }}>✓ {file.name}</div>}
            <div style={{ marginTop: 8, fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              MP3 · WAV · M4A · OGG · FLAC · WebM · MP4 · Max 500 MB
            </div>
          </div>
        </div>
      )}

      <div className="flex gap-3">
        <button className="btn btn-primary btn-lg" onClick={handleCreate}>
          {mode === 'IMPORT' ? 'Upload & Process' : mode === 'OVERLAY' ? 'Launch Overlay' : 'Create Meeting'}
        </button>
        <button className="btn btn-secondary btn-lg" onClick={() => navigate('/meetings')}>Cancel</button>
      </div>
    </div>
  )
}
