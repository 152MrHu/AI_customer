import { http } from './request'

export const knowledgeApi = {
  createKb: (data) => http.post('/api/knowledge/bases', data),
  listKbs: (params) => http.get('/api/knowledge/bases', params),
  deleteKb: (kbId) => http.delete(`/api/knowledge/bases/${kbId}`),
  uploadDocument: (kbId, file) => {
    const formData = new FormData()
    formData.append('file', file)
    return http.upload(`/api/knowledge/bases/${kbId}/documents`, formData)
  },
  listDocuments: (kbId, params) => http.get(`/api/knowledge/bases/${kbId}/documents`, params),
  deleteDocument: (docId) => http.delete(`/api/knowledge/documents/${docId}`),
}
