import { getToken, clearAuth } from '../utils/auth'

const BASE = import.meta.env.VITE_API_BASE || ''

async function request(url, options = {}) {
  const token = getToken()
  // FormData 时由浏览器自动设置 Content-Type (multipart/form-data; boundary=...)
  // 不手动指定，否则后端无法正确解析文件字段
  const isFormData = options.body instanceof FormData
  const headers = isFormData
    ? { ...(options.headers || {}) }
    : { 'Content-Type': 'application/json', ...(options.headers || {}) }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch(`${BASE}${url}`, { ...options, headers })

  // 如果不是 JSON（如 SSE），直接返回 response
  const contentType = resp.headers.get('content-type') || ''
  if (!contentType.includes('application/json')) {
    return resp
  }

  const data = await resp.json()

  if (data.code === 401) {
    clearAuth()
    window.location.href = '/login'
    throw new Error('未授权，请重新登录')
  }

  if (data.code !== 200) {
    throw new Error(data.message || '请求失败')
  }

  return data.data
}

export const http = {
  get: (url, params) => {
    const qs = params ? '?' + new URLSearchParams(params).toString() : ''
    return request(`${url}${qs}`)
  },
  post: (url, body) => request(url, { method: 'POST', body: JSON.stringify(body) }),
  put: (url, body) => request(url, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (url) => request(url, { method: 'DELETE' }),
  upload: (url, formData) => request(url, { method: 'POST', body: formData }),
}
