import React, { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Table,
  Button,
  Input,
  Select,
  Space,
  Typography,
  message,
  Tag,
  Switch,
  Popconfirm,
  Modal,
  Form,
} from 'antd'
import {
  ReloadOutlined,
  SearchOutlined,
  DeleteOutlined,
  UserAddOutlined,
} from '@ant-design/icons'
import { userApi } from '../../api/user'
import { formatTime } from '../../utils/format'

const { Title, Text } = Typography

const ROLE_MAP = {
  admin: { label: '管理员', color: 'purple' },
  agent: { label: '客服', color: 'blue' },
  user: { label: '普通用户', color: 'default' },
}

export default function UserManage() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState(undefined)
  const [roleFilter, setRoleFilter] = useState(undefined)

  // 创建客服弹窗
  const [agentModalOpen, setAgentModalOpen] = useState(false)
  const [agentForm] = Form.useForm()
  const [creatingAgent, setCreatingAgent] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize }
      if (keyword) params.keyword = keyword
      if (statusFilter !== undefined && statusFilter !== null) {
        params.status = statusFilter
      }
      if (roleFilter) params.role = roleFilter
      const res = await userApi.list(params)
      setData(res.items || [])
      setTotal(res.total || 0)
    } catch (e) {
      message.error(e.message || '加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, keyword, statusFilter, roleFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleStatusChange = async (userId, checked) => {
    const newStatus = checked ? 1 : 0
    try {
      await userApi.updateStatus(userId, newStatus)
      message.success(checked ? '已启用' : '已禁用')
      setData((prev) =>
        prev.map((u) => (u.user_id === userId ? { ...u, status: newStatus } : u))
      )
    } catch (e) {
      message.error(e.message || '更新状态失败')
    }
  }

  const handleRoleChange = async (userId, newRole) => {
    try {
      await userApi.updateRole(userId, newRole)
      message.success('角色已更新')
      setData((prev) =>
        prev.map((u) => (u.user_id === userId ? { ...u, role: newRole } : u))
      )
    } catch (e) {
      message.error(e.message || '更新角色失败')
    }
  }

  const handleDelete = async (userId) => {
    try {
      await userApi.delete(userId)
      message.success('已删除用户')
      loadData()
    } catch (e) {
      message.error(e.message || '删除失败')
    }
  }

  const handleCreateAgent = async (values) => {
    setCreatingAgent(true)
    try {
      await userApi.createAgent(values)
      message.success(`客服账号 ${values.username} 创建成功`)
      setAgentModalOpen(false)
      agentForm.resetFields()
      loadData()
    } catch (e) {
      message.error(e.message || '创建客服失败')
    } finally {
      setCreatingAgent(false)
    }
  }

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '手机号',
      dataIndex: 'phone',
      key: 'phone',
      width: 140,
      render: (t) => t || '-',
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
      ellipsis: true,
      render: (t) => t || <Text type="secondary">-</Text>,
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      width: 130,
      render: (role, record) => {
        const info = ROLE_MAP[role] || ROLE_MAP.user
        return (
          <Select
            size="small"
            value={role}
            style={{ width: 110 }}
            onChange={(newRole) => handleRoleChange(record.user_id, newRole)}
            options={[
              { label: '普通用户', value: 'user' },
              { label: '客服', value: 'agent' },
              { label: '管理员', value: 'admin' },
            ]}
          />
        )
      },
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status, record) => (
        <Switch
          checked={status === 1}
          checkedChildren="启用"
          unCheckedChildren="禁用"
          onChange={(checked) => handleStatusChange(record.user_id, checked)}
        />
      ),
    },
    {
      title: '注册时间',
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
          title="确定删除该用户吗？"
          description="此操作不可恢复"
          okText="删除"
          cancelText="取消"
          okButtonProps={{ danger: true }}
          onConfirm={() => handleDelete(record.user_id)}
        >
          <Button type="link" danger icon={<DeleteOutlined />} size="small">
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <Card
      title={
        <Title level={5} style={{ margin: 0 }}>
          用户管理
        </Title>
      }
      extra={
        <Space>
          <Button
            type="primary"
            icon={<UserAddOutlined />}
            onClick={() => setAgentModalOpen(true)}
          >
            创建客服
          </Button>
          <Button icon={<ReloadOutlined />} onClick={loadData}>
            刷新
          </Button>
        </Space>
      }
    >
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          placeholder="搜索用户名/手机号/邮箱"
          style={{ width: 260 }}
          value={keyword}
          onChange={(e) => {
            setKeyword(e.target.value)
            setPage(1)
          }}
          onPressEnter={loadData}
        />
        <Select
          allowClear
          placeholder="状态筛选"
          style={{ width: 120 }}
          value={statusFilter}
          onChange={(v) => {
            setStatusFilter(v)
            setPage(1)
          }}
          options={[
            { label: '启用', value: 1 },
            { label: '禁用', value: 0 },
          ]}
        />
        <Select
          allowClear
          placeholder="角色筛选"
          style={{ width: 120 }}
          value={roleFilter}
          onChange={(v) => {
            setRoleFilter(v)
            setPage(1)
          }}
          options={[
            { label: '管理员', value: 'admin' },
            { label: '客服', value: 'agent' },
            { label: '普通用户', value: 'user' },
          ]}
        />
        <Button type="primary" onClick={loadData}>
          查询
        </Button>
      </Space>

      <Table
        rowKey="user_id"
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

      {/* 创建客服 Modal */}
      <Modal
        title="创建客服账号"
        open={agentModalOpen}
        onCancel={() => {
          setAgentModalOpen(false)
          agentForm.resetFields()
        }}
        footer={null}
        destroyOnClose
      >
        <Form
          form={agentForm}
          layout="vertical"
          onFinish={handleCreateAgent}
          style={{ marginTop: 16 }}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { pattern: /^[a-zA-Z0-9_]{3,20}$/, message: '3-20位字母/数字/下划线' },
            ]}
          >
            <Input placeholder="客服登录账号" maxLength={20} />
          </Form.Item>
          <Form.Item
            name="phone"
            label="手机号"
            rules={[
              { required: true, message: '请输入手机号' },
              { pattern: /^1[3-9]\d{9}$/, message: '请输入有效的11位手机号' },
            ]}
          >
            <Input placeholder="11位手机号" maxLength={11} />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱（选填）"
            rules={[{ type: 'email', message: '请输入有效的邮箱地址' }]}
          >
            <Input placeholder="选填" />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 8, message: '密码至少8位' },
              {
                pattern: /^(?=.*[a-zA-Z])(?=.*\d)/,
                message: '需包含字母和数字',
              },
            ]}
          >
            <Input.Password placeholder="至少8位，包含字母和数字" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
            <Space>
              <Button
                onClick={() => {
                  setAgentModalOpen(false)
                  agentForm.resetFields()
                }}
              >
                取消
              </Button>
              <Button type="primary" htmlType="submit" loading={creatingAgent}>
                创建
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </Card>
  )
}
