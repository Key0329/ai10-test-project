const BASE = '/api/v1';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
  const es = new EventSource(`${BASE}/jobs/${jobId}/logs`);
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

export async function rerunJob(jobId, credentials) {
  return request(`/jobs/${jobId}/rerun`, { method: 'POST', body: JSON.stringify(credentials) });
}

export async function getJobChain(jobId) {
  return request(`/jobs/${jobId}/chain`);
}

export async function healthCheck() {
  return request('/health');
}

export async function getMcpList() {
  return request('/mcp/list');
}

export async function testMcpServers(selectedMcps, mcpTokens = {}) {
  return request('/mcp/test', {
    method: 'POST',
    body: JSON.stringify({ selected_mcps: selectedMcps, mcp_tokens: mcpTokens }),
  });
}

export async function scanRepoMcp(repoUrl, branch, githubToken) {
  return request('/mcp/scan', {
    method: 'POST',
    body: JSON.stringify({ repo_url: repoUrl, branch: branch || null, github_token: githubToken }),
  });
}
