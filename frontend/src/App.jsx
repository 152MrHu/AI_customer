import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ProtectedRoute from './components/common/ProtectedRoute'
import Login from './pages/Login'
import Register from './pages/Register'
import Chat from './pages/Chat'
import Profile from './pages/Profile'
import AdminLayout from './layouts/AdminLayout'
import KnowledgeManage from './pages/admin/KnowledgeManage'
import DocumentManage from './pages/admin/DocumentManage'
import UserManage from './pages/admin/UserManage'
import AgentLayout from './layouts/AgentLayout'
import AgentWorkspace from './pages/agent/AgentWorkspace'
import AgentChat from './pages/agent/AgentChat'

function RootRedirect() {
  const { token } = useAuth()
  return <Navigate to={token ? '/chat' : '/login'} replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/chat"
        element={
          <ProtectedRoute>
            <Chat />
          </ProtectedRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin"
        element={
          <ProtectedRoute requireAdmin>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route path="knowledge" element={<KnowledgeManage />} />
        <Route path="documents" element={<DocumentManage />} />
        <Route path="users" element={<UserManage />} />
        <Route index element={<Navigate to="knowledge" replace />} />
      </Route>
      <Route
        path="/agent"
        element={
          <ProtectedRoute requireAgent>
            <AgentLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<AgentWorkspace />} />
        <Route path="my" element={<AgentWorkspace />} />
      </Route>
      <Route
        path="/agent/chat/:sessionId"
        element={
          <ProtectedRoute requireAgent>
            <AgentChat />
          </ProtectedRoute>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
