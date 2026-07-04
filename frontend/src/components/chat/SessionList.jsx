import React, { useState, useMemo } from 'react'
import { Input, Button, List, Typography, Popconfirm, Empty, Spin, theme } from 'antd'
import {
  PlusOutlined,
  SearchOutlined,
  DeleteOutlined,
  MessageOutlined,
} from '@ant-design/icons'
import { formatTime } from '../../utils/format'

const { Text, Paragraph } = Typography

export default function SessionList({
  sessions,
  currentId,
  loading,
  onSelect,
  onCreate,
  onDelete,
}) {
  const [keyword, setKeyword] = useState('')
  const { token: themeToken } = theme.useToken()

  const filtered = useMemo(() => {
    if (!keyword.trim()) return sessions
    const kw = keyword.toLowerCase()
    return sessions.filter(
      (s) =>
        (s.title || '').toLowerCase().includes(kw) ||
        (s.preview || '').toLowerCase().includes(kw)
    )
  }, [sessions, keyword])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{ padding: '12px 12px 8px' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          block
          onClick={onCreate}
          style={{ marginBottom: 12 }}
        >
          新建会话
        </Button>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="搜索会话"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
        />
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '0 8px' }}>
        {loading ? (
          <div style={{ textAlign: 'center', padding: 24 }}>
            <Spin />
          </div>
        ) : filtered.length === 0 ? (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无会话"
            style={{ marginTop: 40 }}
          />
        ) : (
          <List
            dataSource={filtered}
            renderItem={(item) => {
              const active = item.session_id === currentId
              return (
                <div
                  key={item.session_id}
                  onClick={() => onSelect(item.session_id)}
                  style={{
                    cursor: 'pointer',
                    padding: '10px 12px',
                    borderRadius: 8,
                    marginBottom: 4,
                    background: active ? themeToken.colorPrimaryBg : 'transparent',
                    border: active
                      ? `1px solid ${themeToken.colorPrimaryBorder}`
                      : '1px solid transparent',
                    transition: 'all 0.2s',
                    position: 'relative',
                  }}
                  className="session-item"
                >
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      marginBottom: 4,
                    }}
                  >
                    <Text
                      strong
                      ellipsis
                      style={{ flex: 1, color: active ? themeToken.colorPrimaryText : undefined }}
                    >
                      <MessageOutlined style={{ marginRight: 6 }} />
                      {item.title || '新会话'}
                    </Text>
                    <Popconfirm
                      title="确定删除该会话吗？"
                      okText="删除"
                      cancelText="取消"
                      okButtonProps={{ danger: true }}
                      onConfirm={(e) => {
                        e?.stopPropagation()
                        onDelete(item.session_id)
                      }}
                      onCancel={(e) => e?.stopPropagation()}
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        onClick={(e) => e.stopPropagation()}
                        className="session-delete-btn"
                        style={{ opacity: 0.5 }}
                      />
                    </Popconfirm>
                  </div>
                  {item.preview && (
                    <Text
                      type="secondary"
                      ellipsis
                      style={{ fontSize: 12, display: 'block' }}
                    >
                      {item.preview}
                    </Text>
                  )}
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {formatTime(item.updated_at || item.created_at)}
                  </Text>
                </div>
              )
            }}
          />
        )}
      </div>
    </div>
  )
}
