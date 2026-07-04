import React, { useState } from 'react'
import { Layout, Menu, Avatar, Button, Space, theme } from 'antd'
import {
  BookOutlined,
  FileTextOutlined,
  UserOutlined,
  LogoutOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const { Header, Sider, Content } = Layout

const menuItems = [
  {
    key: '/admin/knowledge',
    icon: <BookOutlined />,
    label: '知识库管理',
  },
  {
    key: '/admin/documents',
    icon: <FileTextOutlined />,
    label: '文档管理',
  },
  {
    key: '/admin/users',
    icon: <UserOutlined />,
    label: '用户管理',
  },
]

export default function AdminLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const { token: themeToken } = theme.useToken()

  // 计算当前选中的菜单项
  const selectedKey =
    menuItems.find((m) => location.pathname.startsWith(m.key))?.key || '/admin/knowledge'

  const handleMenuClick = ({ key }) => {
    navigate(key)
  }

  const handleLogout = async () => {
    setLoggingOut(true)
    await logout()
    setLoggingOut(false)
    navigate('/login', { replace: true })
  }

  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        theme="light"
        style={{ borderRight: `1px solid ${themeToken.colorBorderSecondary}` }}
      >
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: collapsed ? 16 : 18,
            color: themeToken.colorPrimary,
            borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
          }}
        >
          {collapsed ? 'AI' : 'AI 客服管理'}
        </div>
        <Menu
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={handleMenuClick}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 24px',
            background: themeToken.colorBgContainer,
            borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
          }}
        >
          <Space>
            <Button
              type="text"
              icon={<ArrowLeftOutlined />}
              onClick={() => navigate('/chat')}
            >
              返回聊天
            </Button>
          </Space>
          <Space size="middle">
            <Avatar icon={<UserOutlined />} style={{ background: themeToken.colorPrimary }} />
            <span>{user?.username || '管理员'}</span>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              loading={loggingOut}
              onClick={handleLogout}
            />
          </Space>
        </Header>
        <Content style={{ padding: 24, overflow: 'auto', background: themeToken.colorBgLayout }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
