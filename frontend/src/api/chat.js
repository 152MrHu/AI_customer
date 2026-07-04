import { http } from './request'

export const chatApi = {
  createSession: (knowledgeBaseId) => http.post('/api/chat/sessions', { knowledge_base_id: knowledgeBaseId }),
  listSessions: (params) => http.get('/api/chat/sessions', params),
  sessionDetail: (sessionId) => http.get(`/api/chat/sessions/${sessionId}`),
  deleteSession: (sessionId) => http.delete(`/api/chat/sessions/${sessionId}`),
}
