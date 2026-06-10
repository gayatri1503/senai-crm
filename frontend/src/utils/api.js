import axios from 'axios'

const API = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000,
})

export const fetchDashboardStats = () => API.get('/dashboard/stats')
export const fetchThreads = (email) => API.get(`/threads/${email}`)
export const fetchSentimentTrend = (days = 1000) => API.get(`/analytics/sentiment-trend?days=${days}`)
export const fetchCategoryBreakdown = (days = 1000) => API.get(`/analytics/category-breakdown?days=${days}`)
export const fetchAtRiskAccounts = () => API.get('/analytics/at-risk-accounts')
export const searchRAG = (query, topK = 3) => API.get(`/rag/search?q=${encodeURIComponent(query)}&top_k=${topK}`)
export const ingestEmail = (payload) => API.post('/api/ingest', payload)
export const runAgentDryRun = (emailId) => API.post(`/agent/dry-run/${emailId}`)
export const runAgent = (emailId) => API.post(`/agent/run/${emailId}`)
export const fetchAllEmails = (status = null) => {
  const params = status ? `?status=${status}` : ''
  return API.get(`/api/emails${params}`)
}

export default API