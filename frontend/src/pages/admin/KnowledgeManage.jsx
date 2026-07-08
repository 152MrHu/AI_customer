import React, { useState, useEffect, useCallback, useMemo } from 'react'
import {
  Card,
  Table,
  Button,
  Modal,
  Form,
  Input,
  Space,
  Typography,
  message,
  Tag,
  Popconfirm,
  Tabs,
} from 'antd'
import { PlusOutlined, ReloadOutlined, FileTextOutlined, DeleteOutlined, TeamOutlined, UserOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { knowledgeApi } from '../../api/knowledge'
import { useAuth } from '../../context/AuthContext'
import { formatTime } from '../../utils/format'

const { Title, Text } = Typography

export default function KnowledgeManage() {
  const { isAdmin } = useAuth()
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [modalOpen, setModalOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [activeTab, setActiveTab] = useState('all')
  const [form] = Form.useForm()
  const navigate = useNavigate()

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      if (isAdmin) {
        const res = await knowledgeApi.listKbs({ page, page_size: pageSize })
        setData(res.items || [])
        setTotal(res.total || 0)
      } else {
        const res = await knowledgeApi.listAvailableKbs()
        const list = Array.isArray(res) ? res : (res.items || [])
        setData(list)
        setTotal(list.length)
      }
    } catch (e) {
      message.error(e.message || '加载知识库失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, isAdmin])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleCreate = async () => {
    try {
      const values = await form.validateFields()
      setCreating(true)
      await knowledgeApi.createKb(values)
      message.success('创建成功')
      setModalOpen(false)
      form.resetFields()
      loadData()
    } catch (e) {
      if (e?.errorFields) return
      message.error(e.message || '创建失败')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (kbId, kbName) => {
    try {
      await knowledgeApi.deleteKb(kbId)
      message.success(`知识库「${kbName}」已删除`)
      loadData()
    } catch (e) {
      message.error(e.message || '删除失败')
    }
  }

  // 分组：公共知识库 vs 我的知识库
  const { publicKbs, myKbs } = useMemo(() => {
    const publicList = data.filter((d) => d.owner_id == null)
    const myList = data.filter((d) => d.owner_id != null)
    return { publicKbs: publicList, myKbs: myList }
  }, [data])

  const publicColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || <Text type="secondary">-</Text>,
    },
    {
      title: '文档数',
      dataIndex: 'document_count',
      key: 'document_count',
      width: 100,
      align: 'center',
      render: (n) => <Tag color="blue">{n ?? 0}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t) => formatTime(t),
    },
  ]

  const myColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || <Text type="secondary">-</Text>,
    },
    {
      title: '文档数',
      dataIndex: 'document_count',
      key: 'document_count',
      width: 100,
      align: 'center',
      render: (n) => <Tag color="blue">{n ?? 0}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t) => formatTime(t),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/admin/documents?kb_id=${record.kb_id}`)}
          >
            管理文档
          </Button>
          <Popconfirm
            title="确认删除"
            description={`删除知识库「${record.name}」将同时删除所有文档和向量数据，此操作不可撤销！`}
            onConfirm={() => handleDelete(record.kb_id, record.name)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 管理员：全部列（含归属标签 + 操作）
  const adminColumns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text) => text || <Text type="secondary">-</Text>,
    },
    {
      title: '归属',
      dataIndex: 'owner_id',
      key: 'owner_id',
      width: 100,
      align: 'center',
      render: (ownerId) =>
        ownerId ? (
          <Tag icon={<UserOutlined />} color="blue">用户</Tag>
        ) : (
          <Tag icon={<TeamOutlined />} color="green">公共</Tag>
        ),
    },
    {
      title: '文档数',
      dataIndex: 'document_count',
      key: 'document_count',
      width: 100,
      align: 'center',
      render: (n) => <Tag color="blue">{n ?? 0}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (t) => formatTime(t),
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<FileTextOutlined />}
            onClick={() => navigate(`/admin/documents?kb_id=${record.kb_id}`)}
          >
            管理文档
          </Button>
          <Popconfirm
            title="确认删除"
            description={`删除知识库「${record.name}」将同时删除所有文档和向量数据，此操作不可撤销！`}
            onConfirm={() => handleDelete(record.kb_id, record.name)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  // 管理员：Tab 过滤
  const adminFiltered = activeTab === 'public'
    ? data.filter((d) => d.owner_id == null)
    : activeTab === 'user'
    ? data.filter((d) => d.owner_id != null)
    : data

  return (
    <div>
      {/* ===== 非管理员视图：仅显示自己的知识库 ===== */}
      {!isAdmin && (
        <Card
          title={
            <Space>
              <UserOutlined />
              <Title level={5} style={{ margin: 0 }}>我的知识库</Title>
              <Tag color="blue">个人创建</Tag>
            </Space>
          }
          extra={
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                创建知识库
              </Button>
            </Space>
          }
        >
          <Table
            rowKey="kb_id"
            columns={myColumns}
            dataSource={myKbs}
            loading={loading}
            pagination={false}
            locale={{ emptyText: '你还没有创建知识库，点击右上角「创建知识库」开始' }}
          />
        </Card>
      )}

      {/* ===== 管理员视图：全部 + Tab 筛选 ===== */}
      {isAdmin && (
        <Card
          title={
            <Space>
              <Title level={5} style={{ margin: 0 }}>知识库管理</Title>
              <Text type="secondary" style={{ fontSize: 12 }}>(管理员 - 查看全部)</Text>
            </Space>
          }
          extra={
            <Space>
              <Button icon={<ReloadOutlined />} onClick={loadData}>刷新</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
                创建知识库
              </Button>
            </Space>
          }
        >
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            style={{ marginBottom: -16 }}
            items={[
              { key: 'all', label: `全部 (${data.length})` },
              { key: 'public', label: `公共知识库 (${publicKbs.length})` },
              { key: 'user', label: `用户自建 (${myKbs.length})` },
            ]}
          />
          <Table
            rowKey="kb_id"
            columns={adminColumns}
            dataSource={adminFiltered}
            loading={loading}
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
      )}

      <Modal
        title="创建知识库"
        open={modalOpen}
        onCancel={() => {
          setModalOpen(false)
          form.resetFields()
        }}
        onOk={handleCreate}
        confirmLoading={creating}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="名称"
            rules={[
              { required: true, message: '请输入知识库名称' },
              { max: 50, message: '名称不超过 50 个字符' },
            ]}
          >
            <Input placeholder="请输入知识库名称" />
          </Form.Item>
          <Form.Item
            name="description"
            label="描述"
            rules={[{ max: 200, message: '描述不超过 200 个字符' }]}
          >
            <Input.TextArea rows={3} placeholder="可选，简要描述知识库用途" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
