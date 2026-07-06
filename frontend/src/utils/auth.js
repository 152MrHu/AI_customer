const TOKEN_KEY = 'ai_cs_token'
const USER_KEY = 'ai_cs_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function removeToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function getUser() {
  const u = localStorage.getItem(USER_KEY)
  return u ? JSON.parse(u) : null
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function removeUser() {
  localStorage.removeItem(USER_KEY)
}

export function clearAuth() {
  removeToken()
  removeUser()
}

export function isLoggedIn() {
  return !!getToken()
}

export function isAdmin() {
  const u = getUser()
  return u?.role === 'admin'
}

export function isAgent() {
  const u = getUser()
  return u?.role === 'agent' || u?.role === 'admin'
}
