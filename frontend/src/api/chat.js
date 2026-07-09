import { http } from './request'

export const chatApi = {
  createSession: (knowledgeBaseId, mode = 'kb') => http.post('/api/chat/sessions', { knowledge_base_id: knowledgeBaseId, mode }),
  listSessions: (params) => http.get('/api/chat/sessions', params),
  sessionDetail: (sessionId) => http.get(`/api/chat/sessions/${sessionId}`),
  deleteSession: (sessionId) => http.delete(`/api/chat/sessions/${sessionId}`),
  submitFeedback: (messageId, data) => http.post(`/api/chat/messages/${messageId}/feedback`, data),
  createHandoff: (sessionId, data) => http.post(`/api/chat/sessions/${sessionId}/handoff`, data),

  /** 上传文件/图片，提取文字 */
  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.upload('/api/chat/upload', formData)
  },
  /** 生成 Word 文档 */
  generateDoc: (sessionId, data) => http.post(`/api/chat/sessions/${sessionId}/generate-doc`, data),
  /** 下载文档 URL */
  getDocDownloadUrl: (fileName) => `/api/chat/documents/${fileName}`,

  // Agent / Handoff APIs
  getAllTickets: (params) => http.get('/api/chat/handoff/tickets', params),
  getPendingTickets: (params) => http.get('/api/chat/handoff/tickets', { ...params, status: 'pending' }),
  getMyTickets: (params) => http.get('/api/chat/handoff/tickets', { ...params, claimed_by: 'me' }),
  getPendingCount: () => http.get('/api/chat/handoff/pending-count'),
  claimTicket: (ticketId) => http.put(`/api/chat/handoff/${ticketId}/claim`),
  resolveTicket: (ticketId, data) => http.put(`/api/chat/handoff/${ticketId}/resolve`, data),
  sendAgentMessage: (sessionId, content) => http.post(`/api/chat/sessions/${sessionId}/agent-message`, { content }),
}
