import React, { createContext, useContext, useState, useCallback } from 'react'
import { getToken, getUser, setToken, setUser, clearAuth } from '../utils/auth'
import { userApi } from '../api/user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setTokenState] = useState(getToken())
  const [user, setUserState] = useState(getUser())

  const login = useCallback((newToken, newUser) => {
    setToken(newToken)
    setUser(newUser)
    setTokenState(newToken)
    setUserState(newUser)
  }, [])

  const logout = useCallback(async () => {
    try {
      await userApi.logout()
    } catch (e) {
      // 忽略登出接口错误，仍然清除本地状态
    }
    clearAuth()
    setTokenState(null)
    setUserState(null)
  }, [])

  const refreshUser = useCallback(async () => {
    try {
      const u = await userApi.me()
      setUser(u)
      setUserState(u)
      return u
    } catch (e) {
      return null
    }
  }, [])

  const value = {
    token,
    user,
    login,
    logout,
    refreshUser,
    isAdmin: user?.role === 'admin',
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth 必须在 AuthProvider 内使用')
  }
  return ctx
}
