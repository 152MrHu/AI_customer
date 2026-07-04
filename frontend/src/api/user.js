import { http } from './request'

export const userApi = {
  register: (data) => http.post('/api/user/register', data),
  login: (data) => http.post('/api/user/login', data),
  logout: () => http.post('/api/user/logout'),
  me: () => http.get('/api/user/me'),
  list: (params) => http.get('/api/user/list', params),
  updateStatus: (userId, status) => http.put(`/api/user/${userId}/status`, { status }),
  delete: (userId) => http.delete(`/api/user/${userId}`),
}
