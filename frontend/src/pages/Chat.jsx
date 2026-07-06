import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Layout, Typography, Empty, message, theme, Segmented, Select, Button, Modal, Input, Alert, Tag } from 'antd'
import { RobotOutlined, BookOutlined, GlobalOutlined, CustomerServiceOutlined, SyncOutlined } from '@ant-design/icons'
import MainLayout from '../layouts/MainLayout'
import SessionList from '../components/chat/SessionList'
import MessageList from '../components/chat/MessageList'
import MessageInput from '../components/chat/MessageInput'
import { chatApi } from '../api/chat'
import { knowledgeApi } from '../api/knowledge'
import { streamChat } from '../api/sse'

const { Sider, Content } = Layout
const { Title, Text } = Typography

let msgIdCounter = 0
const genMsgId = () => `local-${Date.now()}-${msgIdCounter++}`

export default function Chat() {
  const [sessions, setSessions] = useState([])
  const [currentSessionId, setCurrentSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [sessionDetail, setSessionDetail] = useState(null)
  const [createMode, setCreateMode] = useState('kb')
  const [knowledgeBases, setKnowledgeBases] = useState([])
  const [selectedKbId, setSelectedKbId] = useState(null)
  const [handoffOpen, setHandoffOpen] = useState(false)
  const [handoffReason, setHandoffReason] = useState('')
  const [handoffLoading, setHandoffLoading] = useState(false)
  const [handoffTicket, setHandoffTicket] = useState(null)  // 当前会话的转人工工单
  const streamAbortRef = useRef(false)
  const pollRef = useRef(null)
  const { token: themeToken } = theme.useToken()

  const loadSessions = useCallback(async () => {
    setSessionsLoading(true)
    try {
      const data = await chatApi.listSessions({ page: 1, page_size: 50 })
      const list = data.items || []
      setSessions(list)
      return list
    } catch (e) {
      message.error(e.message || '加载会话列表失败')
      return []
    } finally {
      setSessionsLoading(false)
    }
  }, [])

  // 加载知识库列表
  const loadKnowledgeBases = useCallback(async () => {
    try {
      const data = await knowledgeApi.listKbs({ page: 1, page_size: 50 })
      const list = data.items || []
      setKnowledgeBases(list)
      // 默认选中第一个知识库
      if (list.length > 0 && selectedKbId === null) {
        setSelectedKbId(list[0].kb_id || list[0].id)
      }
    } catch (e) {
      // 静默失败，知识库列表加载失败不影响对话
      console.error('加载知识库列表失败:', e)
    }
  }, [])

  useEffect(() => {
    loadSessions()
    loadKnowledgeBases()
  }, [loadSessions, loadKnowledgeBases])

  const loadSessionDetail = useCallback(async (sessionId) => {
    setMessagesLoading(true)
    try {
      const data = await chatApi.sessionDetail(sessionId)
      setSessionDetail(data)
      const history = (data.messages || []).map((m) => ({
        id: m.message_id != null ? String(m.message_id) : genMsgId(),
        role: m.role,
        content: m.content,
        sources: m.sources || [],
        created_at: m.created_at,
      }))
      setMessages(history)
    } catch (e) {
      message.error(e.message || '加载会话详情失败')
      setMessages([])
    } finally {
      setMessagesLoading(false)
    }
  }, [])

  // 查询当前会话的转人工工单
  const checkHandoffTicket = useCallback(async (sessionId) => {
    try {
      // 使用 getAllTickets（不带 claimed_by），普通用户后端自动过滤为自己的工单
      const data = await chatApi.getAllTickets({ page: 1, page_size: 20 })
      const ticket = (data.items || []).find((t) => t.session_id === parseInt(sessionId, 10))
      setHandoffTicket(ticket || null)
      return ticket
    } catch {
      return null
    }
  }, [])

  const handleSelectSession = useCallback(
    (sessionId) => {
      if (sessionId === currentSessionId) return
      setCurrentSessionId(sessionId)
      setHandoffTicket(null)
      loadSessionDetail(sessionId)
      checkHandoffTicket(sessionId)
    },
    [currentSessionId, loadSessionDetail, checkHandoffTicket]
  )

  // 有转人工工单时，每 5 秒自动刷新消息（接收客服回复）
  useEffect(() => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
    if (!currentSessionId) return

    pollRef.current = setInterval(async () => {
      // 刷新工单状态
      const ticket = await checkHandoffTicket(currentSessionId)
      // 有活跃工单（pending/claimed）时自动刷新消息
      if (ticket && (ticket.status === 'pending' || ticket.status === 'claimed')) {
        try {
          const data = await chatApi.sessionDetail(currentSessionId)
          const history = (data.messages || []).map((m) => ({
            id: m.message_id != null ? String(m.message_id) : genMsgId(),
            role: m.role,
            content: m.content,
            sources: m.sources || [],
            created_at: m.created_at,
          }))
          setMessages((prev) => {
            // 只在新消息数量不同时才更新，避免闪烁
            if (history.length !== prev.length) return history
            return prev
          })
        } catch { /* 静默 */ }
      }
      // 工单已解决/关闭时停止轮询（下次切换会话时重置）
      if (ticket && (ticket.status === 'resolved' || ticket.status === 'closed')) {
        if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      }
    }, 5000)

    return () => { if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null } }
  }, [currentSessionId, checkHandoffTicket])

  const handleCreateSession = useCallback(async () => {
    // kb 模式下必须选择知识库
    const kbId = createMode === 'kb' ? selectedKbId : null
    if (createMode === 'kb' && !kbId) {
      message.warning('请先选择知识库')
      return
    }
    try {
      const data = await chatApi.createSession(kbId, createMode)
      const newSession = {
        session_id: data.session_id,
        title: data.title,
        mode: data.mode || createMode,
        created_at: data.created_at,
        updated_at: data.created_at,
        preview: '',
      }
      setSessions((prev) => [newSession, ...prev])
      setCurrentSessionId(data.session_id)
      setSessionDetail(data)
      setMessages([])
      message.success('已创建新会话')
    } catch (e) {
      message.error(e.message || '创建会话失败')
    }
  }, [createMode, selectedKbId])

  const handleDeleteSession = useCallback(
    async (sessionId) => {
      try {
        await chatApi.deleteSession(sessionId)
        message.success('已删除会话')
        if (sessionId === currentSessionId) {
          setCurrentSessionId(null)
          setMessages([])
          setSessionDetail(null)
        }
        setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      } catch (e) {
        message.error(e.message || '删除会话失败')
      }
    },
    [currentSessionId]
  )

  const handleHandoff = useCallback(async () => {
    setHandoffLoading(true)
    try {
      const result = await chatApi.createHandoff(currentSessionId, { reason: handoffReason || undefined })
      message.success('已提交转人工请求，请耐心等待客服接入')
      setHandoffOpen(false)
      setHandoffReason('')
      // 立即设置工单信息，显示"等待客服接入"
      setHandoffTicket({ ticket_id: result.ticket_id, status: 'pending' })
    } catch (e) {
      message.error(e.message || '提交转人工请求失败')
    } finally {
      setHandoffLoading(false)
    }
  }, [currentSessionId, handoffReason])

  const handleSend = useCallback(
    async (content) => {
      if (!currentSessionId) {
        message.warning('请先选择或创建一个会话')
        return
      }
      if (streaming) return

      const userMsg = {
        id: genMsgId(),
        role: 'user',
        content,
        sources: [],
      }
      const aiMsgId = genMsgId()
      const aiMsg = {
        id: aiMsgId,
        role: 'assistant',
        content: '',
        sources: [],
      }
      setMessages((prev) => [...prev, userMsg, aiMsg])
      setStreaming(true)
      streamAbortRef.current = false

      await streamChat(currentSessionId, content, {
        onToken: (token) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === aiMsgId ? { ...m, content: m.content + token } : m))
          )
        },
        onSources: (sources) => {
          setMessages((prev) =>
            prev.map((m) => (m.id === aiMsgId ? { ...m, sources } : m))
          )
        },
        onDone: () => {
          setStreaming(false)
          // 刷新会话列表以更新预览和时间
          loadSessions()
        },
        onError: (errMsg, code) => {
          setStreaming(false)
          setMessages((prev) =>
            prev.map((m) =>
              m.id === aiMsgId
                ? {
                    ...m,
                    content: m.content || `抱歉，发生错误：${errMsg || '未知错误'}`,
                  }
                : m
            )
          )
          if (errMsg) message.error(errMsg)
        },
      })

      // 兜底：若流异常结束未触发 done
      setStreaming(false)
    },
    [currentSessionId, streaming, loadSessions]
  )

  return (
    <MainLayout>
      <Layout style={{ height: '100%' }}>
        <Sider
          width={300}
          theme="light"
          style={{
            background: themeToken.colorBgContainer,
            borderRight: `1px solid ${themeToken.colorBorderSecondary}`,
          }}
        >
          <SessionList
            sessions={sessions}
            currentId={currentSessionId}
            loading={sessionsLoading}
            onSelect={handleSelectSession}
            onCreate={handleCreateSession}
            onDelete={handleDeleteSession}
            createMode={createMode}
            onModeChange={setCreateMode}
            knowledgeBases={knowledgeBases}
            selectedKbId={selectedKbId}
            onKbChange={setSelectedKbId}
          />
        </Sider>
        <Content style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
          {currentSessionId ? (
            <>
              <div
                style={{
                  padding: '12px 24px',
                  borderBottom: `1px solid ${themeToken.colorBorderSecondary}`,
                  background: themeToken.colorBgContainer,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                }}
              >
                <Title level={5} style={{ margin: 0 }}>
                  {sessionDetail?.title || '当前会话'}
                </Title>
                {sessionDetail?.mode === 'assistant' ? (
                  <Text style={{ color: themeToken.colorPrimary, fontSize: 12 }}>
                    <GlobalOutlined /> 通用助手模式
                  </Text>
                ) : (
                  <Text style={{ color: themeToken.colorTextSecondary, fontSize: 12 }}>
                    <BookOutlined /> 知识库模式
                  </Text>
                )}
                {/* 转人工工单状态 */}
                {handoffTicket && (
                  <Tag
                    icon={handoffTicket.status === 'claimed' ? <SyncOutlined spin /> : undefined}
                    color={
                      handoffTicket.status === 'pending' ? 'orange' :
                      handoffTicket.status === 'claimed' ? 'blue' :
                      handoffTicket.status === 'resolved' ? 'green' : 'default'
                    }
                  >
                    {handoffTicket.status === 'pending' ? '等待客服接入' :
                     handoffTicket.status === 'claimed' ? '客服处理中' :
                     handoffTicket.status === 'resolved' ? '已解决' : '已关闭'}
                  </Tag>
                )}
                <div style={{ flex: 1 }} />
                <Button
                  type="primary"
                  ghost
                  size="small"
                  icon={<CustomerServiceOutlined />}
                  onClick={() => setHandoffOpen(true)}
                  disabled={!!handoffTicket}
                >
                  {handoffTicket ? '已转人工' : '转人工'}
                </Button>
              </div>

              <Modal
                title="转人工客服"
                open={handoffOpen}
                onCancel={() => setHandoffOpen(false)}
                footer={null}
                destroyOnClose
              >
                <div style={{ padding: '8px 0' }}>
                  <p style={{ marginBottom: 16, color: themeToken.colorTextSecondary }}>
                    您即将发起转人工请求，请简要描述您的问题：
                  </p>
                  <Input.TextArea
                    rows={4}
                    placeholder="请输入您的问题描述（选填）..."
                    value={handoffReason}
                    onChange={(e) => setHandoffReason(e.target.value)}
                    style={{ marginBottom: 16 }}
                  />
                  <div style={{ textAlign: 'right' }}>
                    <Button
                      style={{ marginRight: 8 }}
                      onClick={() => setHandoffOpen(false)}
                    >
                      取消
                    </Button>
                    <Button
                      type="primary"
                      loading={handoffLoading}
                      onClick={handleHandoff}
                    >
                      确认转人工
                    </Button>
                  </div>
                </div>
              </Modal>

              <MessageList
                messages={messages}
                loading={messagesLoading}
                streaming={streaming}
              />
              <MessageInput
                onSend={handleSend}
                disabled={streaming || messagesLoading}
                placeholder={
                  handoffTicket?.status === 'claimed'
                    ? '人工客服已接入，请输入您的问题...'
                    : '输入您的问题，Enter 发送...'
                }
              />
            </>
          ) : (
            <div
              style={{
                flex: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                background: themeToken.colorBgLayout,
                gap: 16,
              }}
            >
              <RobotOutlined style={{ fontSize: 64, color: themeToken.colorPrimary }} />
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={
                  <Text type="secondary">
                    请从左侧选择一个会话，或点击「新建会话」开始对话
                  </Text>
                }
              />
            </div>
          )}
        </Content>
      </Layout>
    </MainLayout>
  )
}
