import { useState } from 'react'
import { createJob } from '../api'

const DEFAULT_REPOS = [
  // Add your team's repos here
  // 'https://github.com/your-org/repo-a.git',
  // 'https://github.com/your-org/repo-b.git',
]

export default function NewJob({ onCreated, onBack }) {
  const [form, setForm] = useState({
    repo_url: '',
    jira_ticket: '',
    branch: '',
    extra_prompt: '',
    priority: 3,
    requested_by: localStorage.getItem('cra_user') || '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  function update(key, value) {
    setForm(prev => ({ ...prev, [key]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.repo_url || !form.jira_ticket) {
      setError('Repo URL and Jira Ticket are required')
      return
    }
    setError('')
    setSubmitting(true)

    // Remember user name
    if (form.requested_by) {
      localStorage.setItem('cra_user', form.requested_by)
    }

    try {
      const res = await createJob({
        repo_url: form.repo_url,
        jira_ticket: form.jira_ticket.toUpperCase(),
        branch: form.branch || undefined,
        extra_prompt: form.extra_prompt || undefined,
        priority: form.priority,
        requested_by: form.requested_by || undefined,
      })
      onCreated(res.job_id)
    } catch (e) {
      setError(e.message)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <button className="back-btn" onClick={onBack}>← Back to Dashboard</button>

      <div style={{ border: '1px solid var(--border)', borderRadius: 10, background: 'var(--surface)', padding: 20, marginTop: 12 }}>
        <div className="section-title">New Job</div>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Repository URL *</label>
            {DEFAULT_REPOS.length > 0 ? (
              <>
                <select
                  className="form-select"
                  value={form.repo_url}
                  onChange={e => update('repo_url', e.target.value)}
                >
                  <option value="">Select a repo or type below</option>
                  {DEFAULT_REPOS.map(r => (
                    <option key={r} value={r}>{r.replace('https://github.com/', '')}</option>
                  ))}
                </select>
                <input
                  className="form-input"
                  style={{ marginTop: 6 }}
                  value={form.repo_url}
                  onChange={e => update('repo_url', e.target.value)}
                  placeholder="or enter URL manually"
                />
              </>
            ) : (
              <input
                className="form-input"
                value={form.repo_url}
                onChange={e => update('repo_url', e.target.value)}
                placeholder="https://github.com/org/repo.git"
              />
            )}
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Jira Ticket *</label>
              <input
                className="form-input"
                value={form.jira_ticket}
                onChange={e => update('jira_ticket', e.target.value)}
                placeholder="JRA-123"
              />
            </div>
            <div className="form-group">
              <label className="form-label">Branch <span style={{ color: 'var(--text-hint)' }}>(optional)</span></label>
              <input
                className="form-input"
                value={form.branch}
                onChange={e => update('branch', e.target.value)}
                placeholder="main"
              />
            </div>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label className="form-label">Priority</label>
              <select className="form-select" value={form.priority} onChange={e => update('priority', parseInt(e.target.value))}>
                <option value={1}>1 — Urgent</option>
                <option value={2}>2 — High</option>
                <option value={3}>3 — Normal</option>
                <option value={4}>4 — Low</option>
                <option value={5}>5 — Background</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Your Name <span style={{ color: 'var(--text-hint)' }}>(optional)</span></label>
              <input
                className="form-input"
                value={form.requested_by}
                onChange={e => update('requested_by', e.target.value)}
                placeholder="Your name"
              />
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Extra Prompt <span style={{ color: 'var(--text-hint)' }}>(optional, max 2000 chars)</span></label>
            <textarea
              className="form-textarea"
              value={form.extra_prompt}
              onChange={e => update('extra_prompt', e.target.value)}
              placeholder="Additional instructions for Claude..."
              maxLength={2000}
              rows={3}
            />
          </div>

          <button className="btn" type="submit" disabled={submitting}>
            {submitting ? 'Submitting...' : '→ Submit Job'}
          </button>
        </form>
      </div>
    </div>
  )
}
