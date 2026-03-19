import { useState } from 'react'
import { setToken, healthCheck } from '../api'

export default function TokenGate({ onSaved }) {
  const [value, setValue] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!value.trim()) return
    setChecking(true)
    setError('')
    setToken(value.trim())
    try {
      await healthCheck()
      onSaved()
    } catch {
      setError('Unable to connect. Check the token and server URL.')
      setToken('')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="token-gate">
      <div className="token-card">
        <h2>Claude Remote Agent</h2>
        <p>Enter the API token to connect to the server.</p>
        {error && <div className="alert alert-error">{error}</div>}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">API Token</label>
            <input
              type="password"
              className="form-input"
              value={value}
              onChange={e => setValue(e.target.value)}
              placeholder="your-secret-token"
              autoFocus
            />
          </div>
          <button className="btn" type="submit" disabled={checking}>
            {checking ? 'Connecting...' : 'Connect'}
          </button>
        </form>
      </div>
    </div>
  )
}
