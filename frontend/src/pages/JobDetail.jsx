import { useState, useEffect, useRef } from 'react'
import { getJob, cancelJob, streamLogs } from '../api'
import StatusBadge from '../components/StatusBadge'

const FILTER_OPTIONS = [
  { key: 'all', label: 'All' },
  { key: 'assistant', label: 'Assistant' },
  { key: 'tool', label: 'Tools' },
  { key: 'system', label: 'System' },
]

export default function JobDetail({ jobId, onBack }) {
  const [job, setJob] = useState(null)
  const [logs, setLogs] = useState([])
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const logRef = useRef(null)
  const streamRef = useRef(null)

  useEffect(() => {
    let interval
    async function load() {
      try {
        const data = await getJob(jobId)
        setJob(data)
      } catch (e) {
        setError(e.message)
      }
    }
    load()
    interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [jobId])

  useEffect(() => {
    if (!job) return
    const isActive = ['queued', 'cloning', 'running', 'pushing'].includes(job.status)
    if (!isActive && streamRef.current) {
      streamRef.current()
      streamRef.current = null
    }
    if (isActive && !streamRef.current) {
      streamRef.current = streamLogs(
        jobId,
        (line) => {
          setLogs(prev => [...prev, line])
          if (logRef.current) {
            logRef.current.scrollTop = logRef.current.scrollHeight
          }
        },
        () => { streamRef.current = null }
      )
    }
    return () => {
      if (streamRef.current) { streamRef.current(); streamRef.current = null }
    }
  }, [job?.status, jobId])

  async function handleCancel() {
    if (!confirm('Cancel this job?')) return
    try {
      await cancelJob(jobId)
      const data = await getJob(jobId)
      setJob(data)
    } catch (e) {
      setError(e.message)
    }
  }

  function elapsed() {
    if (!job) return '-'
    const start = new Date(job.created_at)
    const end = job.finished_at ? new Date(job.finished_at) : new Date()
    const s = Math.round((end - start) / 1000)
    if (s < 60) return `${s}s`
    return `${Math.floor(s / 60)}m ${s % 60}s`
  }

  function lineClass(entry) {
    if (entry.stream === 'error') return 'log-line log-line-error'
    if (entry.stream === 'stderr') return 'log-line log-line-stderr'
    if (entry.stream === 'system') return 'log-line log-line-system'
    if (entry.event_type === 'assistant') return 'log-line log-line-stdout'
    if (entry.event_type === 'tool_use' || entry.event_type === 'tool_result') return 'log-line log-line-system'
    return 'log-line'
  }

  function matchesFilter(entry) {
    if (filter === 'all') return true
    if (filter === 'assistant') return entry.event_type === 'assistant'
    if (filter === 'tool') return entry.event_type === 'tool_use' || entry.event_type === 'tool_result'
    if (filter === 'system') return entry.stream === 'system' || entry.stream === 'error'
    return true
  }

  const filteredLogs = logs.filter(matchesFilter)

  if (!job && !error) return <div className="empty">Loading...</div>
  if (error) return <div className="alert alert-error">{error}</div>
  if (!job) return null

  const isActive = ['queued', 'cloning', 'running', 'pushing'].includes(job.status)

  return (
    <div>
      <button className="back-btn" onClick={onBack}>← Back to Dashboard</button>

      <div className="detail-header" style={{ marginTop: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className="detail-ticket">{job.jira_ticket}</span>
          <StatusBadge status={job.status} />
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{elapsed()}</div>
      </div>

      <div className="detail-meta">
        <div className="meta-item">
          <div className="meta-label">Repository</div>
          <div className="meta-value">{job.repo_url}</div>
        </div>
        <div className="meta-item">
          <div className="meta-label">Branch</div>
          <div className="meta-value">{job.branch || 'default'}</div>
        </div>
        <div className="meta-item">
          <div className="meta-label">Requested by</div>
          <div className="meta-value">{job.requested_by || '-'}</div>
        </div>
        <div className="meta-item">
          <div className="meta-label">Priority</div>
          <div className="meta-value">{job.priority}</div>
        </div>
        <div className="meta-item">
          <div className="meta-label">Created</div>
          <div className="meta-value">{new Date(job.created_at).toLocaleString('zh-TW')}</div>
        </div>
        <div className="meta-item">
          <div className="meta-label">Job ID</div>
          <div className="meta-value">{job.job_id}</div>
        </div>
      </div>

      {job.pr_url && (
        <div className="alert alert-success">
          PR created: <a href={job.pr_url} target="_blank" rel="noopener" style={{ color: 'inherit' }}>{job.pr_url}</a>
        </div>
      )}
      {job.error_message && (
        <div className="alert alert-error">{job.error_message}</div>
      )}
      {job.extra_prompt && (
        <div style={{ marginBottom: 14 }}>
          <div className="section-title">Extra Prompt</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)', padding: '10px 14px', background: 'var(--surface)', borderRadius: 8, border: '1px solid var(--border)' }}>
            {job.extra_prompt}
          </div>
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 16 }}>
        <div className="section-title" style={{ margin: 0 }}>
          Logs {isActive && <span style={{ color: 'var(--blue)' }}>(live)</span>}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {FILTER_OPTIONS.map(opt => (
            <button
              key={opt.key}
              className={`btn btn-sm${filter === opt.key ? ' btn-active' : ''}`}
              style={{ fontSize: 11, padding: '2px 8px', borderRadius: 4, border: '1px solid var(--border)', background: filter === opt.key ? 'var(--blue)' : 'var(--surface)', color: filter === opt.key ? '#fff' : 'var(--text-dim)', cursor: 'pointer' }}
              onClick={() => setFilter(opt.key)}
            >
              {opt.label}
            </button>
          ))}
        </div>
      </div>
      <div className="log-viewer" ref={logRef}>
        {filteredLogs.length === 0 ? (
          <div style={{ color: 'var(--text-hint)' }}>
            {isActive ? 'Waiting for output...' : 'No logs available.'}
          </div>
        ) : (
          filteredLogs.map((entry, i) => (
            <div key={i} className={lineClass(entry)}>
              <span style={{ color: 'var(--text-hint)', marginRight: 6 }}>[{entry.event_type || entry.stream}]</span>
              {entry.message}
            </div>
          ))
        )}
      </div>

      {isActive && (
        <button
          className="btn btn-danger"
          style={{ marginTop: 14 }}
          onClick={handleCancel}
        >
          Cancel Job
        </button>
      )}
    </div>
  )
}
