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
    throw new Error(err.detail || `HTTP ${res.status}`);
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
  const es = new EventSource(`${BASE}/jobs/${jobId}/logs`);
  es.addEventListener('log', (e) => onLog(e.data));
  es.addEventListener('done', (e) => { onDone(e.data); es.close(); });
  es.onerror = () => { es.close(); };
  return () => es.close();
}

export async function healthCheck() {
  return request('/health');
}
