import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Card, Table, Button, Input, Modal, Typography, message, Tag, Space, Tabs, Badge,
} from 'antd'
import {
  ReloadOutlined, CheckCircleOutlined, FormOutlined, EyeOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, useOutletContext } from 'react-router-dom'
import { chatApi } from '../../api/chat'
import { formatTime } from '../../utils/format'
import { useAuth } from '../../context/AuthContext'

const { Title, Text } = Typography

// ── 工单列表 子 Tab ──
const LIST_TABS = {
  all:        { key: 'all',        label: '全部工单', params: {} },
  pending:    { key: 'pending',    label: '未认领',   params: { status: 'pending' } },
  claimed:    { key: 'claimed',    label: '已认领',   params: { status: 'claimed' } },
  unresolved: { key: 'unresolved', label: '未处理',   params: { status: 'pending,claimed' } },
  resolved:   { key: 'resolved',   label: '已处理',   params: { status: 'resolved,closed' } },
}

// ── 我的工单 子 Tab ──
const MY_TABS = {
  all:        { key: 'my_all',        label: '所有认领', params: { claimed_by: 'me' } },
  unresolved: { key: 'my_unresolved', label: '未处理',   params: { claimed_by: 'me', status: 'claimed' } },
  resolved:   { key: 'my_resolved',   label: '已处理',   params: { claimed_by: 'me', status: 'resolved,closed' } },
}

const STATUS_MAP = { pending: { color: 'orange', label: '待处理' }, claimed: { color: 'blue', label: '处理中' }, resolved: { color: 'green', label: '已解决' }, closed: { color: 'default', label: '已关闭' } }

export default function AgentWorkspace() {
  const navigate = useNavigate()
  const location = useLocation()
  const outletCtx = useOutletContext()
  const { user } = useAuth()
  const setPendingCount = outletCtx?.setPendingCount

  const isMyTickets = location.pathname === '/agent/my'
  const tabsConfig = isMyTickets ? MY_TABS : LIST_TABS

  const [activeTab, setActiveTab] = useState(isMyTickets ? 'my_all' : 'pending')

  // 每 tab 独立分页 store
  const [tabData, setTabData] = useState(() => {
    const s = {}
    Object.keys(LIST_TABS).forEach((k) => { s[k] = { data: [], total: 0, loading: false } })
    Object.keys(MY_TABS).forEach((k) => { s[k] = { data: [], total: 0, loading: false } })
    return s
  })
  const pageRef = useRef({})
  // 确保每个 tab key 有 page store
  const getPage = (k) => { if (!pageRef.current[k]) pageRef.current[k] = { page: 1, pageSize: 10 }; return pageRef.current[k] }

  // 解决弹窗
  const [resolveOpen, setResolveOpen] = useState(false)
  const [resolveTicketId, setResolveTicketId] = useState(null)
  const [resolveContent, setResolveContent] = useState('')
  const [resolveLoading, setResolveLoading] = useState(false)

  const pollRef = useRef(null)

  // ── 加载 ──
  const loadTab = useCallback(async (tabKey) => {
    const cfg = tabsConfig[tabKey]
    if (!cfg) return
    const pg = getPage(tabKey)
    setTabData((prev) => ({ ...prev, [tabKey]: { ...prev[tabKey], loading: true } }))
    try {
      const data = await chatApi.getAllTickets({ ...cfg.params, page: pg.page, page_size: pg.pageSize })
      const items = data.items || []
      setTabData((prev) => ({ ...prev, [tabKey]: { data: items, total: data.total || 0, loading: false } }))
      if (tabKey === 'pending' && setPendingCount) setPendingCount(data.total ?? items.length)
    } catch (e) {
      message.error(e.message || '加载失败')
      setTabData((prev) => ({ ...prev, [tabKey]: { ...prev[tabKey], loading: false } }))
    }
  }, [tabsConfig, setPendingCount])

  useEffect(() => { loadTab(activeTab) }, [activeTab, loadTab])

  useEffect(() => {
    pollRef.current = setInterval(() => loadTab(activeTab), 10000)
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [activeTab, loadTab])

  // ── 操作 ──
  const refreshAfterAction = () => {
    loadTab(activeTab)
    // 同时刷新关联 tab
    if (isMyTickets) Object.keys(MY_TABS).forEach((k) => { if (k !== activeTab) loadTab(k) })
    else { loadTab('pending'); loadTab('all') }
  }

  const handleClaim = async (ticketId) => {
    try { await chatApi.claimTicket(ticketId); message.success('已认领'); refreshAfterAction() }
    catch (e) { message.error(e.message || '认领失败') }
  }

  const handleResolve = async () => {
    if (!resolveContent.trim()) { message.warning('请输入解决内容'); return }
    setResolveLoading(true)
    try { await chatApi.resolveTicket(resolveTicketId, { resolution: resolveContent }); message.success('已解决'); setResolveOpen(false); refreshAfterAction() }
    catch (e) { message.error(e.message || '解决失败') }
    finally { setResolveLoading(false) }
  }

  // ── 表格列 ──
  const columns = [
    { title: '工单ID', dataIndex: 'ticket_id', width: 90, render: (id) => <Text code>#{id}</Text> },
    { title: '用户名', dataIndex: 'username', width: 100, render: (t) => <Text strong>{t || '-'}</Text> },
    { title: '原因', dataIndex: 'reason', ellipsis: true, render: (t) => t || <Text type="secondary">用户请求转人工</Text> },
    { title: '状态', dataIndex: 'status', width: 90,
      render: (s) => { const m = STATUS_MAP[s] || {}; return <Tag color={m.color || 'default'}>{m.label || s}</Tag> } },
    { title: '认领人', dataIndex: 'claimed_by', width: 80,
      render: (cb) => !cb ? <Text type="secondary">-</Text> : String(cb) === String(user?.user_id) ? <Tag color="blue">我</Tag> : <Text>{cb}</Text> },
    { title: '创建时间', dataIndex: 'created_at', width: 160, render: (t) => formatTime(t) },
    { title: '操作', key: 'action', width: 160,
      render: (_, r) => {
        const isMine = String(r.claimed_by) === String(user?.user_id)
        if (r.status === 'pending') return <Button type="primary" size="small" icon={<FormOutlined />} onClick={() => handleClaim(r.ticket_id)}>认领</Button>
        if (r.status === 'claimed' && isMine) return (
          <Space>
            <Button type="primary" size="small" icon={<FormOutlined />} onClick={() => navigate(`/agent/chat/${r.session_id}`)}>处理</Button>
            <Button size="small" icon={<CheckCircleOutlined />} onClick={() => { setResolveTicketId(r.ticket_id); setResolveContent(''); setResolveOpen(true) }}>解决</Button>
          </Space>
        )
        if (r.status === 'claimed' && !isMine) return <Text type="secondary">已被他人处理</Text>
        if (r.status === 'resolved' || r.status === 'closed') return r.session_id ? <Button size="small" icon={<EyeOutlined />} onClick={() => navigate(`/agent/chat/${r.session_id}`)}>查看</Button> : null
        return null
      } },
  ]

  // ── Render ──
  const pendingTotal = tabData.pending?.total || 0

  const tabItems = Object.entries(tabsConfig).map(([key, cfg]) => {
    const td = tabData[key] || { data: [], total: 0, loading: false }
    const pg = getPage(key)
    return {
      key,
      label: key === 'pending' ? <span>{cfg.label} <Badge count={pendingTotal} size="small" style={{ marginLeft: 4 }} /></span> : cfg.label,
      children: (
        <>
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
            <Button size="small" icon={<ReloadOutlined />} onClick={() => loadTab(key)}>刷新</Button>
          </div>
          <Table rowKey="ticket_id" columns={columns} dataSource={td.data} loading={td.loading} size="middle"
            pagination={{ current: pg.page, pageSize: pg.pageSize, total: td.total, showSizeChanger: true, showTotal: (t) => `共 ${t} 条`,
              onChange: (p, ps) => { pageRef.current[key] = { page: p, pageSize: ps }; loadTab(key) } }}
            locale={{ emptyText: '暂无工单' }} />
        </>
      ),
    }
  })

  return (
    <>
      <Card title={<Title level={5} style={{ margin: 0 }}>{isMyTickets ? '我的工单' : '工单列表'}</Title>} style={{ marginBottom: 0 }}>
        <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
      </Card>
      <Modal title="解决工单" open={resolveOpen} onCancel={() => setResolveOpen(false)} footer={null} destroyOnClose>
        <div style={{ padding: '8px 0' }}>
          <p style={{ marginBottom: 16, color: '#666' }}>请输入工单解决内容：</p>
          <Input.TextArea rows={4} placeholder="请输入解决内容..." value={resolveContent}
            onChange={(e) => setResolveContent(e.target.value)} style={{ marginBottom: 16 }} />
          <div style={{ textAlign: 'right' }}>
            <Button style={{ marginRight: 8 }} onClick={() => setResolveOpen(false)}>取消</Button>
            <Button type="primary" loading={resolveLoading} onClick={handleResolve}>确认解决</Button>
          </div>
        </div>
      </Modal>
    </>
  )
}
