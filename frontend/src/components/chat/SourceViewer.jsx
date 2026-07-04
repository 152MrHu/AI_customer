import React from 'react'
import { Collapse, Typography, Tag, theme } from 'antd'
import { FileTextOutlined } from '@ant-design/icons'

const { Text, Paragraph } = Typography

export default function SourceViewer({ sources }) {
  const { token: themeToken } = theme.useToken()

  if (!sources || sources.length === 0) return null

  const items = sources.map((src, idx) => {
    const scorePercent = Math.round((src.score || 0) * 100)
    const scoreColor =
      scorePercent >= 80 ? 'green' : scorePercent >= 60 ? 'blue' : 'orange'
    return {
      key: String(idx),
      label: (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 8,
          }}
        >
          <Text ellipsis style={{ flex: 1 }}>
            <FileTextOutlined style={{ marginRight: 6 }} />
            {src.doc_name || `来源 ${idx + 1}`}
          </Text>
          <Tag color={scoreColor} style={{ marginLeft: 8 }}>
            相似度 {scorePercent}%
          </Tag>
        </div>
      ),
      children: (
        <div>
          {src.snippet ? (
            <Paragraph
              type="secondary"
              style={{ marginBottom: 0, whiteSpace: 'pre-wrap' }}
            >
              {src.snippet}
            </Paragraph>
          ) : (
            <Text type="secondary">无预览内容</Text>
          )}
        </div>
      ),
    }
  })

  return (
    <div style={{ maxWidth: 600 }}>
      <Collapse
        items={items}
        size="small"
        ghost
        style={{
          background: themeToken.colorBgContainer,
          border: `1px solid ${themeToken.colorBorderSecondary}`,
          borderRadius: 8,
          padding: '0 8px',
        }}
      />
    </div>
  )
}
