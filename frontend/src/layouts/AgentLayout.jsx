import React, { useState } from 'react'
import { Layout, Menu, Avatar, Button, Space, Badge, theme } from 'antd'
import {
  CustomerServiceOutlined,
  UnorderedListOutlined,
  UserOutlined,
  LogoutOutlined,
  ArrowLeftOutlined,
  OrderedListOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { chatApi } from '../api/chat'

const { Header, Sider, Content } = Layout

export default function AgentLayout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [collapsed, setCollapsed] = useState(false)
  const [loggingOut, setLoggingOut] = useState(false)
  const [pendingCount, setPendingCount] = useState(0)
  const { token: themeToken } = theme.useToken()

  // 加载待处理数量
  React.useEffect(() => {
    const loadCount = async () => {
      try {
        const data = await chatApi.getPendingCount()
        setPendingCount(data.count || 0)
      } catch (e) {
        // 静默
      }
    }
    loadCount()
    const interval = setInterval(loadCount, 10000)
    return () => clearInterval(interval)
  }, [])

  const menuItems = [
    {
      key: '/agent',
      icon: (
        <Badge count={pendingCount} size="small" offset={[2, -2]}>
          <UnorderedListOutlined />
        </Badge>
      ),
      label: '工单队列',
    },
    {
      key: '/agent/my',
      icon: <OrderedListOutlined />,
      label: '我的工单',
    },
  ]

  const selectedKey =
    menuItems.find((m) => location.pathname === m.key || (m.key !== '/agent' && location.pathname.startsWith(m.key)))?.key ||
    (location.pathname.startsWith('/agent/chat') ? '/agent/my' : '/agent')

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
          {collapsed ? 'CS' : 'AI 客服工作台'}
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
            <span>{(user?.role === 'admin' ? '管理员' : '客服') + ' ' + (user?.username || '')}</span>
            <Button
              type="text"
              icon={<LogoutOutlined />}
              loading={loggingOut}
              onClick={handleLogout}
            />
          </Space>
        </Header>
        <Content style={{ padding: 24, overflow: 'auto', background: themeToken.colorBgLayout }}>
          <Outlet context={{ pendingCount, setPendingCount }} />
        </Content>
      </Layout>
    </Layout>
  )
}
