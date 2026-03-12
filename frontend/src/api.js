import axios from 'axios'

const api = axios.create({
    baseURL: '/api',
    timeout: 120000,
})

export default api

// ── Ingestor ──────────────────────────────────────────────────────────────
export const uploadDocuments = (formData) =>
    api.post('/ingestor/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    })

export const extractData = (sessionId, payload) =>
    api.post(`/ingestor/extract/${sessionId}`, payload)

export const getSessionData = (sessionId) =>
    api.get(`/ingestor/session/${sessionId}`)

// ── Research ──────────────────────────────────────────────────────────────
export const runResearch = (payload) =>
    api.post('/research/run', payload)

// ── Recommendation ────────────────────────────────────────────────────────
export const generateRecommendation = (payload) =>
    api.post('/recommendation/generate', payload)

export const getRecommendation = (sessionId) =>
    api.get(`/recommendation/session/${sessionId}`)

export const downloadCAM = (sessionId) =>
    api.get(`/recommendation/cam/${sessionId}`, { responseType: 'blob' })

// ── Health ────────────────────────────────────────────────────────────────
export const checkHealth = () =>
    api.get('/health')
