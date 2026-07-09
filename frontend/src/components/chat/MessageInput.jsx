import React, { useState } from 'react'
import { Input, Button, Upload, Tag, Space, message, Tooltip } from 'antd'
import { SendOutlined, PictureOutlined, FileAddOutlined, CloseOutlined } from '@ant-design/icons'
import { chatApi } from '../../api/chat'

const MAX = 2000

export default function MessageInput({ onSend, disabled, placeholder }) {
  const [value, setValue] = useState('')
  const [uploading, setUploading] = useState(false)
  const [attachment, setAttachment] = useState(null) // { file_name, text, file_type }

  const handleSend = () => {
    const text = value.trim()
    if ((!text && !attachment) || disabled) return
    const attText = attachment?.text || null
    const attName = attachment?.file_name || null
    onSend(text || '请分析以下文件内容', attText, attName)
    setValue('')
    setAttachment(null)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleUpload = async (file, accept) => {
    const ext = (file.name || '').split('.').pop().toLowerCase()
    const isImage = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'].includes(ext)
    const isDoc = ['txt', 'pdf', 'docx', 'md', 'csv'].includes(ext)
    if (!isImage && !isDoc) {
      message.error('仅支持图片(jpg/png/gif/webp)或文档(txt/pdf/docx/md/csv)')
      return false
    }

    setUploading(true)
    try {
      const data = await chatApi.uploadFile(file)
      setAttachment({
        file_name: data.file_name || file.name,
        text: data.text || '',
        file_type: data.file_type || ext,
      })
      message.success(`${isImage ? '图片' : '文件'}「${file.name}」已识别`)
    } catch (e) {
      message.error(e.message || '文件上传失败')
    } finally {
      setUploading(false)
    }
    return false // 阻止 antd 默认上传行为
  }

  return (
    <div>
      {/* 附件预览 */}
      {attachment && (
        <div style={{ padding: '8px 24px 0', display: 'flex', alignItems: 'center', gap: 8 }}>
          <Tag
            closable
            onClose={() => setAttachment(null)}
            closeIcon={<CloseOutlined />}
            color={attachment.file_type === 'jpg' || attachment.file_type === 'png' ? 'purple' : 'blue'}
          >
            {attachment.file_type === 'jpg' || attachment.file_type === 'png' ? '图片' : '文件'}：{attachment.file_name}
            <span style={{ marginLeft: 8, color: '#999', fontSize: 11 }}>
              ({attachment.text.length} 字符)
            </span>
          </Tag>
        </div>
      )}

      <div
        style={{
          padding: '12px 24px',
          borderTop: '1px solid #f0f0f0',
          background: '#fff',
          display: 'flex',
          gap: 8,
          alignItems: 'flex-end',
        }}
      >
        {/* 上传图片 */}
        <Tooltip title="上传图片（OCR识别文字）">
          <Upload
            accept=".jpg,.jpeg,.png,.gif,.webp,.bmp"
            showUploadList={false}
            beforeUpload={(file) => handleUpload(file)}
            disabled={disabled || uploading}
          >
            <Button icon={<PictureOutlined />} disabled={disabled || uploading} />
          </Upload>
        </Tooltip>

        {/* 上传文件 */}
        <Tooltip title="上传文档（提取文字内容）">
          <Upload
            accept=".txt,.pdf,.docx,.md,.csv"
            showUploadList={false}
            beforeUpload={(file) => handleUpload(file)}
            disabled={disabled || uploading}
          >
            <Button icon={<FileAddOutlined />} disabled={disabled || uploading} />
          </Upload>
        </Tooltip>

        <Input.TextArea
          value={value}
          onChange={(e) => setValue(e.target.value.slice(0, MAX))}
          onKeyDown={handleKeyDown}
          placeholder={attachment ? '输入关于文件的问题，或直接发送让AI总结...' : (placeholder || '输入您的问题，Enter 发送，Shift+Enter 换行')}
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
          disabled={disabled || (!value.trim() && !attachment)}
          loading={disabled}
        >
          发送
        </Button>
      </div>
    </div>
  )
}
