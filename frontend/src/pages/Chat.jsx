import React, { useState, useEffect, useCallback, useRef } from 'react'
import { Layout, Typography, Empty, message, theme, Segmented, Select } from 'antd'
import { RobotOutlined, BookOutlined, GlobalOutlined } from '@ant-design/icons'
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
  const streamAbortRef = useRef(false)
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

  const handleSelectSession = useCallback(
    (sessionId) => {
      if (sessionId === currentSessionId) return
      setCurrentSessionId(sessionId)
      loadSessionDetail(sessionId)
    },
    [currentSessionId, loadSessionDetail]
  )

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
              </div>
              <MessageList
                messages={messages}
                loading={messagesLoading}
                streaming={streaming}
              />
              <MessageInput onSend={handleSend} disabled={streaming || messagesLoading} />
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
