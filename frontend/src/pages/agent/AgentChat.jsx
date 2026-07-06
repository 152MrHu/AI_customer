import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Layout,
  Card,
  Typography,
  Tag,
  Button,
  Spin,
  message,
  Space,
  Descriptions,
  Modal,
  Input,
  theme,
} from 'antd'
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  UserOutlined,
  RobotOutlined,
  CustomerServiceOutlined,
} from '@ant-design/icons'
import { useParams, useNavigate } from 'react-router-dom'
import { chatApi } from '../../api/chat'
import { streamAgentMessage } from '../../api/sse'
import { formatTime } from '../../utils/format'

const { Text, Title } = Typography
const { Sider, Content } = Layout

let msgIdCounter = 0
const genMsgId = () => `agent-${Date.now()}-${msgIdCounter++}`

export default function AgentChat() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  const { token: themeToken } = theme.useToken()

  const [sessionDetail, setSessionDetail] = useState(null)
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [ticketInfo, setTicketInfo] = useState(null)
  const [inputValue, setInputValue] = useState('')

  // 解决弹窗
  const [resolveOpen, setResolveOpen] = useState(false)
  const [resolveContent, setResolveContent] = useState('')
  const [resolveLoading, setResolveLoading] = useState(false)

  const messagesEndRef = useRef(null)
  const agentSentIds = useRef(new Set())  // 当前客服发送的消息 ID

  // 加载会话详情和关联工单
  const loadSession = useCallback(async () => {
    setLoading(true)
    try {
      const data = await chatApi.sessionDetail(sessionId)
      setSessionDetail(data)
      const sid = parseInt(sessionId, 10)
      // 查询工单
      const tickets = await chatApi.getMyTickets({ page: 1, page_size: 100 })
      const ticket = (tickets.items || []).find((t) => t.session_id === sid)
      if (ticket) setTicketInfo(ticket)

      // 标记历史消息：如果工单已认领，claim 之后的 assistant 消息视为客服发送
      const claimedAt = ticket?.claimed_at ? new Date(ticket.claimed_at).getTime() : null
      const history = (data.messages || []).map((m) => {
        const msgId = m.message_id != null ? String(m.message_id) : genMsgId()
        const isAgentMsg = m.role === 'assistant' && claimedAt && m.created_at
          ? new Date(m.created_at).getTime() >= claimedAt
          : m.role === 'assistant' && agentSentIds.current.has(msgId)
        if (isAgentMsg) agentSentIds.current.add(msgId)
        return {
          id: msgId,
          role: m.role,
          content: m.content,
          created_at: m.created_at,
          fromAgent: isAgentMsg,
        }
      })
      setMessages(history)
    } catch (e) {
      message.error(e.message || '加载会话详情失败')
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  useEffect(() => {
    if (sessionId) loadSession()
  }, [sessionId, loadSession])

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 发送客服消息
  const handleSend = async () => {
    const text = inputValue.trim()
    if (!text || sending) return

    const agentMsgId = genMsgId()
    agentSentIds.current.add(agentMsgId)
    const agentMsg = {
      id: agentMsgId,
      role: 'assistant',
      content: text,
      fromAgent: true,  // 标记为当前客服发送
    }
    setMessages((prev) => [...prev, agentMsg])
    setInputValue('')
    setSending(true)

    await streamAgentMessage(sessionId, text, {
      onDone: () => {
        setSending(false)
        loadSession()
      },
      onError: (errMsg) => {
        setSending(false)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === agentMsgId
              ? { ...m, content: m.content + `\n[发送失败：${errMsg || '未知错误'}]` }
              : m
          )
        )
        if (errMsg) message.error(errMsg)
      },
    })
    setSending(false)
  }

  // 解决并关闭
  const handleResolve = async () => {
    if (!resolveContent.trim()) {
      message.warning('请输入解决内容')
      return
    }
    setResolveLoading(true)
    try {
      // 查找当前会话的工单（注意：useParams 返回字符串，需转换比较）
      const tickets = await chatApi.getMyTickets({ page: 1, page_size: 100 })
      const sid = parseInt(sessionId, 10)
      const ticket = (tickets.items || []).find((t) => t.session_id === sid)
      if (!ticket) {
        message.error('未找到当前会话的工单，请先在工单队列中认领该工单')
        return
      }
      await chatApi.resolveTicket(ticket.ticket_id, { resolution: resolveContent })
      message.success('工单已解决')
      setResolveOpen(false)
      navigate('/agent/my', { replace: true })
    } catch (e) {
      message.error(e.message || '解决工单失败')
    } finally {
      setResolveLoading(false)
    }
  }

  // 渲染消息气泡
  const renderMessage = (msg) => {
    // 右侧：客服 + AI（服务方）；左侧：用户（客户方）
    const isUser = msg.role === 'user'
    const isRight = !isUser  // 所有 assistant 消息（客服/AI）都在右侧
    const isAgent = !!msg.fromAgent
    const label = isAgent ? '客服' : isUser ? '用户' : 'AI'
    const Icon = isAgent ? CustomerServiceOutlined : isUser ? UserOutlined : RobotOutlined

    return (
      <div
        key={msg.id}
        style={{
          display: 'flex',
          flexDirection: isRight ? 'row-reverse' : 'row',
          gap: 12,
          marginBottom: 20,
          alignItems: 'flex-start',
        }}
      >
        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: isRight ? themeToken.colorPrimary : themeToken.colorBgTextHover,
            color: isRight ? '#fff' : themeToken.colorText,
            flexShrink: 0,
            fontSize: 16,
            fontWeight: 600,
          }}
        >
          <Icon />
        </div>
        <div
          style={{
            maxWidth: '70%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: isRight ? 'flex-end' : 'flex-start',
          }}
        >
          <Text
            type="secondary"
            style={{ fontSize: 11, marginBottom: 4, marginRight: isRight ? 8 : 0, marginLeft: isRight ? 0 : 8 }}
          >
            {label}
          </Text>
          <div
            style={{
              padding: '10px 16px',
              borderRadius: 12,
              background: isRight ? themeToken.colorPrimary : themeToken.colorBgContainer,
              color: isRight ? '#fff' : themeToken.colorText,
              border: isRight ? 'none' : `1px solid ${themeToken.colorBorderSecondary}`,
              boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
              wordBreak: 'break-word',
              whiteSpace: 'pre-wrap',
              lineHeight: 1.6,
            }}
          >
            {msg.content || (sending ? '' : '...')}
          </div>
        </div>
      </div>
    )
  }

  const statusTag = (status) => {
    const colorMap = { pending: 'orange', claimed: 'blue', resolved: 'green', closed: 'default' }
    const labelMap = { pending: '待处理', claimed: '处理中', resolved: '已解决', closed: '已关闭' }
    return <Tag color={colorMap[status] || 'default'}>{labelMap[status] || status}</Tag>
  }

  return (
    <Layout style={{ height: '100vh' }}>
      {/* 左侧：会话信息 */}
      <Sider
        width={300}
        theme="light"
        style={{
          background: themeToken.colorBgContainer,
          borderRight: `1px solid ${themeToken.colorBorderSecondary}`,
          padding: 16,
          overflow: 'auto',
        }}
      >
        <Button
          type="text"
          icon={<ArrowLeftOutlined />}
          onClick={() => navigate('/agent')}
          style={{ marginBottom: 16 }}
        >
          返回工作台
        </Button>

        <Title level={5} style={{ marginTop: 0 }}>
          会话信息
        </Title>

        {loading ? (
          <Spin />
        ) : (
          <>
            <Descriptions column={1} size="small" style={{ marginBottom: 16 }}>
              <Descriptions.Item label="会话标题">
                {sessionDetail?.title || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="会话模式">
                <Tag>{sessionDetail?.mode === 'assistant' ? '通用助手' : '知识库'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {formatTime(sessionDetail?.created_at)}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>工单信息</Title>
            {ticketInfo ? (
              <Descriptions column={1} size="small">
                <Descriptions.Item label="工单ID">
                  <Text code>#{ticketInfo.ticket_id}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="状态">
                  {statusTag(ticketInfo.status)}
                </Descriptions.Item>
                <Descriptions.Item label="用户原因">
                  {ticketInfo.reason || '无'}
                </Descriptions.Item>
                <Descriptions.Item label="创建时间">
                  {formatTime(ticketInfo.created_at)}
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">未关联工单</Text>
            )}

            <div style={{ marginTop: 24 }}>
              <Button
                type="primary"
                icon={<CheckCircleOutlined />}
                block
                onClick={() => setResolveOpen(true)}
              >
                解决并关闭
              </Button>
            </div>
          </>
        )}
      </Sider>

      {/* 右侧：对话区域 */}
      <Layout>
        <Content
          style={{
            display: 'flex',
            flexDirection: 'column',
            height: '100%',
          }}
        >
          {/* 消息列表 */}
          <div
            style={{
              flex: 1,
              overflow: 'auto',
              padding: '16px 24px',
              background: themeToken.colorBgLayout,
            }}
          >
            {loading && (
              <div style={{ textAlign: 'center', padding: 24 }}>
                <Spin tip="加载消息中..." />
              </div>
            )}
            {!loading && messages.length === 0 && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: '100%',
                  color: themeToken.colorTextSecondary,
                }}
              >
                <Text type="secondary">暂无消息记录</Text>
              </div>
            )}
            {messages.map(renderMessage)}
            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 */}
          <div
            style={{
              padding: '12px 24px',
              borderTop: `1px solid ${themeToken.colorBorderSecondary}`,
              background: themeToken.colorBgContainer,
              display: 'flex',
              gap: 12,
              alignItems: 'flex-end',
            }}
          >
            <Input.TextArea
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value.slice(0, 2000))}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="输入回复内容，Enter 发送，Shift+Enter 换行"
              autoSize={{ minRows: 1, maxRows: 6 }}
              disabled={sending || loading}
              maxLength={2000}
              showCount
              style={{ flex: 1, resize: 'none' }}
            />
            <Button
              type="primary"
              onClick={handleSend}
              disabled={!inputValue.trim() || sending}
              loading={sending}
            >
              发送
            </Button>
          </div>
        </Content>
      </Layout>

      {/* 解决弹窗 */}
      <Modal
        title="解决并关闭工单"
        open={resolveOpen}
        onCancel={() => setResolveOpen(false)}
        footer={null}
        destroyOnClose
      >
        <div style={{ padding: '8px 0' }}>
          <p style={{ marginBottom: 16, color: '#666' }}>
            确认解决当前工单吗？请输入解决内容：
          </p>
          <Input.TextArea
            rows={4}
            placeholder="请输入解决内容..."
            value={resolveContent}
            onChange={(e) => setResolveContent(e.target.value)}
            style={{ marginBottom: 16 }}
          />
          <div style={{ textAlign: 'right' }}>
            <Button
              style={{ marginRight: 8 }}
              onClick={() => setResolveOpen(false)}
            >
              取消
            </Button>
            <Button
              type="primary"
              loading={resolveLoading}
              onClick={handleResolve}
            >
              确认解决
            </Button>
          </div>
        </div>
      </Modal>
    </Layout>
  )
}
