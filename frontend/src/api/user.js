import { http } from './request'

export const userApi = {
  register: (data) => http.post('/api/user/register', data),
  login: (data) => http.post('/api/user/login', data),
  logout: () => http.post('/api/user/logout'),
  me: () => http.get('/api/user/me'),
  updateProfile: (data) => http.put('/api/user/profile', data),
  changePassword: (data) => http.put('/api/user/password', data),
  list: (params) => http.get('/api/user/list', params),
  updateStatus: (userId, status) => http.put(`/api/user/${userId}/status`, { status }),
  delete: (userId) => http.delete(`/api/user/${userId}`),
  createAgent: (data) => http.post('/api/user/agents', data),
  listAgents: (params) => http.get('/api/user/agents', params),
  updateRole: (userId, role) => http.put(`/api/user/users/${userId}/role`, { role }),
}
