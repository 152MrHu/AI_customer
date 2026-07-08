import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Card,
  Table,
  Button,
  Select,
  Upload,
  Space,
  Typography,
  message,
  Tag,
  Popconfirm,
  Empty,
} from 'antd'
import { InboxOutlined, ReloadOutlined, DeleteOutlined } from '@ant-design/icons'
import { useSearchParams } from 'react-router-dom'
import { knowledgeApi } from '../../api/knowledge'
import { useAuth } from '../../context/AuthContext'
import { formatTime, formatFileSize } from '../../utils/format'

const { Dragger } = Upload
const { Title, Text } = Typography

const statusMap = {
  pending: { text: '处理中', color: 'processing' },
  ready: { text: '已入库', color: 'success' },
  failed: { text: '失败', color: 'error' },
}

export default function DocumentManage() {
  const { isAdmin } = useAuth()
  const [searchParams] = useSearchParams()
  const [kbList, setKbList] = useState([])
  const [kbId, setKbId] = useState(null)
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [uploading, setUploading] = useState(false)
  const pollTimerRef = useRef(null)

  const loadKbList = useCallback(async () => {
    try {
      let list
      if (isAdmin) {
        const res = await knowledgeApi.listKbs({ page: 1, page_size: 100 })
        list = res.items || []
      } else {
        const res = await knowledgeApi.listAvailableKbs()
        list = Array.isArray(res) ? res : (res.items || [])
      }
      setKbList(list)
      const urlKbId = searchParams.get('kb_id')
      if (urlKbId) {
        setKbId(urlKbId)
      } else if (list.length > 0 && !kbId) {
        setKbId(list[0].kb_id)
      }
    } catch (e) {
      message.error(e.message || '加载知识库列表失败')
    }
  }, [searchParams, kbId, isAdmin])

  useEffect(() => {
    loadKbList()
  }, [loadKbList])

  const loadData = useCallback(async () => {
    if (!kbId) {
      setData([])
      return
    }
    setLoading(true)
    try {
      const res = await knowledgeApi.listDocuments(kbId, { page, page_size: pageSize })
      setData(res.items || [])
      setTotal(res.total || 0)
    } catch (e) {
      message.error(e.message || '加载文档列表失败')
    } finally {
      setLoading(false)
    }
  }, [kbId, page, pageSize])

  useEffect(() => {
    loadData()
  }, [loadData])

  // 轮询 pending 状态的文档
  useEffect(() => {
    const hasPending = data.some((d) => d.status === 'pending')
    if (hasPending) {
      pollTimerRef.current = setInterval(() => {
        loadData()
      }, 5000)
    }
    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current)
        pollTimerRef.current = null
      }
    }
  }, [data, loadData])

  const handleUpload = async (file) => {
    if (!kbId) {
      message.error('请先选择知识库')
      return Upload.LIST_IGNORE
    }
    setUploading(true)
    try {
      await knowledgeApi.uploadDocument(kbId, file)
      message.success(`${file.name} 上传成功`)
      loadData()
    } catch (e) {
      message.error(e.message || `${file.name} 上传失败`)
    } finally {
      setUploading(false)
    }
    // 返回 false 阻止 antd 默认上传行为
    return false
  }

  const handleDelete = async (docId) => {
    try {
      await knowledgeApi.deleteDocument(docId)
      message.success('已删除文档')
      loadData()
    } catch (e) {
      message.error(e.message || '删除失败')
    }
  }

  const columns = [
    {
      title: '文件名',
      dataIndex: 'doc_name',
      key: 'doc_name',
      ellipsis: true,
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '类型',
      dataIndex: 'doc_type',
      key: 'doc_type',
      width: 100,
      render: (t) => t || '-',
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 110,
      render: (s) => formatFileSize(s),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (status) => {
        const cfg = statusMap[status] || { text: status || '-', color: 'default' }
        return <Tag color={cfg.color}>{cfg.text}</Tag>
      },
    },
    {
      title: '切片数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 90,
      align: 'center',
      render: (n) => (n != null ? n : '-'),
    },
    {
      title: '上传时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 170,
      render: (t) => formatTime(t),
    },
    {
      title: '操作',
      key: 'action',
      width: 90,
      render: (_, record) => (
        <Popconfirm
          title="确定删除该文档吗？"
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
          onConfirm={() => handleDelete(record.doc_id)}
        >
          <Button type="link" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div>
      <Card
        title={
          <Title level={5} style={{ margin: 0 }}>
            文档管理
          </Title>
        }
        extra={
          <Space>
            <Select
              placeholder="选择知识库"
              style={{ width: 240 }}
              value={kbId}
              onChange={(v) => {
                setKbId(v)
                setPage(1)
              }}
              options={kbList.map((k) => ({
                label: k.name,
                value: k.kb_id,
              }))}
              notFoundContent="暂无知识库"
            />
            <Button icon={<ReloadOutlined />} onClick={loadData} disabled={!kbId}>
              刷新
            </Button>
          </Space>
        }
      >
        {kbId ? (
          <Dragger
            accept=".pdf,.docx,.txt,.md,.csv"
            multiple={false}
            showUploadList={false}
            beforeUpload={handleUpload}
            disabled={uploading}
            style={{ marginBottom: 16, padding: 16 }}
          >
            <p className="ant-upload-drag-icon">
              <InboxOutlined />
            </p>
            <p className="ant-upload-text">
              {uploading ? '上传中...' : '点击或拖拽文件到此区域上传'}
            </p>
            <p className="ant-upload-hint">
              支持 PDF、Word、TXT、Markdown、CSV 等格式
            </p>
          </Dragger>
        ) : (
          <Empty
            description="请先创建并选择一个知识库"
            style={{ marginBottom: 16, padding: 24 }}
          />
        )}

        <Table
          rowKey="doc_id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="middle"
          pagination={{
            current: page,
            pageSize,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, ps) => {
              setPage(p)
              setPageSize(ps)
            },
          }}
        />
      </Card>
    </div>
  )
}
