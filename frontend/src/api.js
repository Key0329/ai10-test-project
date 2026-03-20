const BASE = '/api/v1';

function getToken() {
  return localStorage.getItem('cra_token') || '';
}

export function setToken(token) {
  localStorage.setItem('cra_token', token);
}

export function getStoredToken() {
  return getToken();
}

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const msg = Array.isArray(detail) ? detail.map(e => e.msg).join('; ') : detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }
  return res.json();
}

export async function createJob(payload) {
  return request('/jobs', { method: 'POST', body: JSON.stringify(payload) });
}

export async function listJobs(status = null, limit = 50) {
  const params = new URLSearchParams({ limit });
  if (status) params.set('status', status);
  return request(`/jobs?${params}`);
}

export async function getJob(jobId) {
  return request(`/jobs/${jobId}`);
}

export async function cancelJob(jobId) {
  return request(`/jobs/${jobId}/cancel`, { method: 'POST' });
}

export function streamLogs(jobId, onLog, onDone) {
  const es = new EventSource(`${BASE}/jobs/${jobId}/logs?token=${getToken()}`);
  es.addEventListener('log', (e) => {
    try {
      const parsed = JSON.parse(e.data);
      onLog(parsed);
    } catch {
      onLog({ stream: 'stdout', message: e.data, event_type: 'raw', metadata: null });
    }
  });
  es.addEventListener('done', (e) => { onDone(e.data); es.close(); });
  es.onerror = () => { es.close(); };
  return () => es.close();
}

export async function rerunJob(jobId) {
  return request(`/jobs/${jobId}/rerun`, { method: 'POST' });
}

export async function getJobChain(jobId) {
  return request(`/jobs/${jobId}/chain`);
}

export async function healthCheck() {
  return request('/health');
}
