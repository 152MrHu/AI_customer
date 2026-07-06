import React, { useEffect, useRef, useState } from 'react'
import { Spin, Typography, theme, Button, Space, message } from 'antd'
import { RobotOutlined, UserOutlined, LikeOutlined, LikeFilled, DislikeOutlined, DislikeFilled } from '@ant-design/icons'
import SourceViewer from './SourceViewer'
import { chatApi } from '../../api/chat'

const { Paragraph } = Typography

export default function MessageList({ messages, loading, streaming }) {
  const bottomRef = useRef(null)
  const { token: themeToken } = theme.useToken()
  const [feedbackMap, setFeedbackMap] = useState({})

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // 初始化反馈状态
  useEffect(() => {
    const initial = {}
    messages.forEach((msg) => {
      if (msg.role === 'assistant' && msg.feedback) {
        initial[msg.id] = msg.feedback
      }
    })
    setFeedbackMap((prev) => ({ ...prev, ...initial }))
  }, [messages])

  const handleFeedback = async (messageId, type) => {
    // 如果已点击同一按钮，取消反馈
    const newValue = feedbackMap[messageId] === type ? null : type
    try {
      await chatApi.submitFeedback(messageId, { feedback: newValue })
      setFeedbackMap((prev) => ({ ...prev, [messageId]: newValue }))
      message.success(newValue ? '感谢您的反馈' : '已取消反馈')
    } catch (e) {
      message.error(e.message || '提交反馈失败')
    }
  }

  const renderAvatar = (role) => {
    const isAi = role === 'assistant'
    return (
      <div
        style={{
          width: 36,
          height: 36,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: isAi ? themeToken.colorPrimary : themeToken.colorBgTextHover,
          color: isAi ? '#fff' : themeToken.colorText,
          flexShrink: 0,
        }}
      >
        {isAi ? <RobotOutlined /> : <UserOutlined />}
      </div>
    )
  }

  return (
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
      {messages.map((msg) => {
        const isUser = msg.role === 'user'
        const isAi = msg.role === 'assistant'
        const showCursor = streaming && isAi && msg.id === messages[messages.length - 1]?.id
        return (
          <div
            key={msg.id}
            style={{
              display: 'flex',
              flexDirection: isUser ? 'row-reverse' : 'row',
              gap: 12,
              marginBottom: 20,
            }}
          >
            {renderAvatar(msg.role)}
            <div
              style={{
                maxWidth: '70%',
                display: 'flex',
                flexDirection: 'column',
                alignItems: isUser ? 'flex-end' : 'flex-start',
              }}
            >
              <div
                style={{
                  padding: '10px 16px',
                  borderRadius: 12,
                  background: isUser ? themeToken.colorPrimary : themeToken.colorBgContainer,
                  color: isUser ? '#fff' : themeToken.colorText,
                  border: isUser
                    ? 'none'
                    : `1px solid ${themeToken.colorBorderSecondary}`,
                  boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
                  wordBreak: 'break-word',
                  whiteSpace: 'pre-wrap',
                  lineHeight: 1.6,
                }}
              >
                {msg.content}
                {showCursor && (
                  <span
                    style={{
                      display: 'inline-block',
                      width: 6,
                      height: 16,
                      marginLeft: 2,
                      background: isUser ? '#fff' : themeToken.colorPrimary,
                      animation: 'blink 1s steps(2) infinite',
                      verticalAlign: 'middle',
                    }}
                  />
                )}
              </div>
              {msg.sources && msg.sources.length > 0 && (
                <div style={{ marginTop: 8, width: '100%' }}>
                  <SourceViewer sources={msg.sources} />
                </div>
              )}
              {isAi && !streaming && msg.content && (
                <div style={{ marginTop: 8, width: '100%' }}>
                  <Space size="small">
                    <Button
                      type="text"
                      size="small"
                      icon={feedbackMap[msg.id] === 'like' ? <LikeFilled /> : <LikeOutlined />}
                      style={{
                        color: feedbackMap[msg.id] === 'like' ? themeToken.colorPrimary : themeToken.colorTextSecondary,
                        fontSize: 13,
                      }}
                      onClick={() => handleFeedback(msg.id, 'like')}
                    />
                    <Button
                      type="text"
                      size="small"
                      icon={feedbackMap[msg.id] === 'dislike' ? <DislikeFilled /> : <DislikeOutlined />}
                      style={{
                        color: feedbackMap[msg.id] === 'dislike' ? themeToken.colorError : themeToken.colorTextSecondary,
                        fontSize: 13,
                      }}
                      onClick={() => handleFeedback(msg.id, 'dislike')}
                    />
                  </Space>
                </div>
              )}
            </div>
          </div>
        )
      })}
      <div ref={bottomRef} />
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </div>
  )
}
