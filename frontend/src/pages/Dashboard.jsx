import { useState, useEffect, useCallback } from 'react'
import { listJobs } from '../api'
import StatusBadge from '../components/StatusBadge'

const FILTERS = [
  { label: 'All', value: null },
  { label: 'Running', value: 'running' },
  { label: 'Queued', value: 'queued' },
  { label: 'Completed', value: 'completed' },
  { label: 'Failed', value: 'failed' },
]

export default function Dashboard({ onNewJob, onSelectJob }) {
  const [data, setData] = useState({ jobs: [], total: 0, running: 0, queued: 0 })
  const [filter, setFilter] = useState(null)
  const [error, setError] = useState('')

  const refresh = useCallback(async () => {
    try {
      const res = await listJobs(filter)
      setData(res)
      setError('')
    } catch (e) {
      setError(e.message)
    }
  }, [filter])

  useEffect(() => {
    refresh()
    const id = setInterval(refresh, 4000)
    return () => clearInterval(id)
  }, [refresh])

  const completed = data.jobs.filter(j => j.status === 'completed').length
  const failed = data.jobs.filter(j => j.status === 'failed').length
  const successRate = completed + failed > 0
    ? Math.round((completed / (completed + failed)) * 100)
    : 0

  function elapsed(job) {
    const start = new Date(job.created_at)
    const end = job.finished_at ? new Date(job.finished_at) : new Date()
    return Math.round((end - start) / 1000)
  }

  function timeAgo(iso) {
    if (!iso) return '-'
    const s = Math.round((Date.now() - new Date(iso)) / 1000)
    if (s < 60) return `${s}s ago`
    if (s < 3600) return `${Math.round(s / 60)}m ago`
    if (s < 86400) return `${Math.round(s / 3600)}h ago`
    return `${Math.round(s / 86400)}d ago`
  }

  return (
    <div>
      {error && <div className="alert alert-error">{error}</div>}

      <div className="stats">
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--blue)' }}>{data.running}</div>
          <div className="stat-label">Running</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--amber)' }}>{data.queued}</div>
          <div className="stat-label">Queued</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{data.total}</div>
          <div className="stat-label">Total</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{ color: 'var(--green)' }}>{successRate}%</div>
          <div className="stat-label">Success Rate</div>
        </div>
      </div>

      <div className="filters">
        {FILTERS.map(f => (
          <button
            key={f.label}
            className={`filter-btn ${filter === f.value ? 'active' : ''}`}
            onClick={() => setFilter(f.value)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {data.jobs.length === 0 ? (
        <div className="empty">
          No jobs yet.{' '}
          <span onClick={onNewJob} style={{ color: 'var(--blue)', cursor: 'pointer' }}>
            Create one
          </span>
        </div>
      ) : (
        data.jobs.map(job => (
          <div key={job.job_id} className="card" onClick={() => onSelectJob(job.job_id)}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <span style={{ fontWeight: 600, fontSize: 14 }}>{job.jira_ticket}</span>
                  <StatusBadge status={job.status} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {job.repo_url.replace('https://github.com/', '')}
                </div>
                {job.requested_by && (
                  <div style={{ fontSize: 11, color: 'var(--text-hint)', marginTop: 2 }}>
                    by {job.requested_by}
                  </div>
                )}
              </div>
              <div style={{ textAlign: 'right', flexShrink: 0 }}>
                <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>{timeAgo(job.created_at)}</div>
                <div style={{ fontSize: 11, color: 'var(--text-hint)', marginTop: 2 }}>{elapsed(job)}s</div>
              </div>
            </div>
            {job.pr_url && (
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--green)' }}>
                PR: {job.pr_url}
              </div>
            )}
            {job.error_message && (
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--red)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {job.error_message}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  )
}
