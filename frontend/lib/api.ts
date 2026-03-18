const BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function api(path: string, options?: RequestInit) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.text()
    throw new Error(err || `API error ${res.status}`)
  }
  return res.json()
}

export const client = {
  // Dashboard
  stats: () => api('/api/dashboard/stats'),

  // Pipeline
  runPipeline: (config?: object) => api('/api/pipeline/run', {
    method: 'POST',
    body: JSON.stringify({ scraper_config: config }),
  }),
  pipelineStatus: (runId: string) => api(`/api/pipeline/status/${runId}`),
  pipelineLogs: (runId: string) => api(`/api/pipeline/logs/${runId}`),

  // Leads
  getLeads: (params?: { stage?: string; urgency?: string }) => {
    const q = new URLSearchParams(params as any).toString()
    return api(`/api/leads${q ? `?${q}` : ''}`)
  },
  createLead: (lead: object) => api('/api/leads', { method: 'POST', body: JSON.stringify(lead) }),
  updateLead: (id: string, updates: object) => api(`/api/leads/${id}`, { method: 'PATCH', body: JSON.stringify(updates) }),
  deleteLead: (id: string) => api(`/api/leads/${id}`, { method: 'DELETE' }),

  // Agents
  runAgent: (agent_name: string, context?: object) => api('/api/agents/run', {
    method: 'POST',
    body: JSON.stringify({ agent_name, context: context || {} }),
  }),
  agentLogs: (agent_name?: string) => api(`/api/agents/logs${agent_name ? `?agent_name=${agent_name}` : ''}`),
  agentDefinitions: () => api('/api/agents/definitions'),

  // Scraper
  runScraper: (config: object) => api('/api/scraper/run', { method: 'POST', body: JSON.stringify(config) }),
  scraperResults: (status?: string) => api(`/api/scraper/results${status ? `?status=${status}` : ''}`),
  approveResult: (id: string) => api(`/api/scraper/results/${id}/approve`, { method: 'PATCH' }),
  rejectResult: (id: string) => api(`/api/scraper/results/${id}/reject`, { method: 'PATCH' }),

  // Outreach
  getOutreach: (status?: string) => api(`/api/outreach${status ? `?status=${status}` : ''}`),
  approveOutreach: (id: string) => api(`/api/outreach/${id}/approve`, { method: 'POST' }),
  sendOutreach: (id: string) => api(`/api/outreach/${id}/send`, { method: 'POST' }),

  // Relationships
  getRelationships: () => api('/api/relationships'),
  getRelRecommendation: (id: string) => api(`/api/relationships/${id}/recommendation`, { method: 'POST' }),
}

// SSE stream for pipeline
export function streamPipeline(runId: string, onUpdate: (data: object) => void) {
  const source = new EventSource(`${BASE}/api/pipeline/stream/${runId}`)
  source.onmessage = (e) => {
    try { onUpdate(JSON.parse(e.data)) } catch {}
  }
  source.onerror = () => source.close()
  return () => source.close()
}
