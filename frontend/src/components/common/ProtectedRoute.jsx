import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function ProtectedRoute({ children, requireAdmin = false, requireAgent = false }) {
  const { token, user, isAdmin, isAgent } = useAuth()
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/chat" replace />
  }

  if (requireAgent && !isAgent) {
    return <Navigate to="/chat" replace />
  }

  // 已登录但 user 信息缺失（如刷新后），仍允许通过，由各页面自行处理
  return children
}
