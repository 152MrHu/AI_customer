import React, { useState } from 'react'
import { Input, Button } from 'antd'
import { SendOutlined } from '@ant-design/icons'

const MAX = 2000

export default function MessageInput({ onSend, disabled, placeholder }) {
  const [value, setValue] = useState('')

  const handleSend = () => {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div
      style={{
        padding: '12px 24px',
        borderTop: '1px solid #f0f0f0',
        background: '#fff',
        display: 'flex',
        gap: 12,
        alignItems: 'flex-end',
      }}
    >
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value.slice(0, MAX))}
        onKeyDown={handleKeyDown}
        placeholder={placeholder || '请输入您的问题，Enter 发送，Shift+Enter 换行'}
        autoSize={{ minRows: 1, maxRows: 6 }}
        disabled={disabled}
        maxLength={MAX}
        showCount
        style={{ flex: 1, resize: 'none' }}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        loading={disabled}
      >
        发送
      </Button>
    </div>
  )
}
