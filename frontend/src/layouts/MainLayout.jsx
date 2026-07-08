import React, { useState } from 'react'
import { Layout, Avatar, Dropdown, Space, Button, theme } from 'antd'
import { UserOutlined, LogoutOutlined, ControlOutlined, MessageOutlined, CustomerServiceOutlined, BookOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const { Header, Content } = Layout

export default function MainLayout({ children }) {
  const { user, logout, isAdmin, isAgent } = useAuth()
  const navigate = useNavigate()
  const [loggingOut, setLoggingOut] = useState(false)
  const { token: themeToken } = theme.useToken()

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
    setLoggingOut(false)
    navigate('/login', { replace: true })
  }

  const menuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: '个人中心',
      onClick: () => navigate('/profile'),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: handleLogout,
    },
  ]

  return (
    <Layout style={{ height: '100vh' }}>
      <Header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 24px',
          background: themeToken.colorBgContainer,
          borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
          boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
        }}
      >
        <Space size="middle">
          <MessageOutlined style={{ fontSize: 20, color: themeToken.colorPrimary }} />
          <span style={{ fontSize: 18, fontWeight: 600 }}>AI 智能客服</span>
        </Space>
        <Space size="middle">
          <Button
            type="text"
            icon={<BookOutlined />}
            onClick={() => navigate('/admin/knowledge')}
          >
            知识库管理
          </Button>
          {isAdmin && (
            <Button
              type="text"
              icon={<ControlOutlined />}
              onClick={() => navigate('/admin')}
            >
              管理后台
            </Button>
          )}
          {isAgent && (
            <Button
              type="text"
              icon={<CustomerServiceOutlined />}
              onClick={() => navigate('/agent')}
            >
              客服工作台
            </Button>
          )}
          <Dropdown menu={{ items: menuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} style={{ background: themeToken.colorPrimary }} />
              <span>{user?.username || '用户'}</span>
            </Space>
          </Dropdown>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            loading={loggingOut}
            onClick={handleLogout}
          />
        </Space>
      </Header>
      <Content style={{ height: 'calc(100vh - 64px)', overflow: 'hidden' }}>{children}</Content>
    </Layout>
  )
}
