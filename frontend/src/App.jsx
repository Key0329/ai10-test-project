import { useState, useEffect } from 'react'
import Dashboard from './pages/Dashboard'
import NewJob from './pages/NewJob'
import JobDetail from './pages/JobDetail'
import TokenGate from './components/TokenGate'
import { getStoredToken } from './api'
import './app.css'

function getRoute() {
  const hash = window.location.hash.slice(1) || '/'
  return hash
}

export default function App() {
  const [route, setRoute] = useState(getRoute)
  const [hasToken, setHasToken] = useState(!!getStoredToken())

  useEffect(() => {
    const onChange = () => setRoute(getRoute())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])

  function navigate(path) {
    window.location.hash = path
  }

  if (!hasToken) {
    return <TokenGate onSaved={() => setHasToken(true)} />
  }

  let page
  if (route === '/new') {
    page = <NewJob onCreated={(id) => navigate(`/jobs/${id}`)} onBack={() => navigate('/')} />
  } else if (route.startsWith('/jobs/')) {
    const jobId = route.replace('/jobs/', '')
    page = <JobDetail jobId={jobId} onBack={() => navigate('/')} />
  } else {
    page = <Dashboard onNewJob={() => navigate('/new')} onSelectJob={(id) => navigate(`/jobs/${id}`)} />
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-left" onClick={() => navigate('/')} style={{ cursor: 'pointer' }}>
          <span className="pulse-dot" />
          <span className="header-title">claude-remote-agent</span>
        </div>
        <nav className="header-nav">
          <button className="nav-btn" onClick={() => navigate('/')}>Dashboard</button>
          <button className="nav-btn primary" onClick={() => navigate('/new')}>+ New Job</button>
        </nav>
      </header>
      <main className="main">{page}</main>
    </div>
  )
}
