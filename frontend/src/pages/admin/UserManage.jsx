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
} from 'antd'
import { ReloadOutlined, SearchOutlined, DeleteOutlined } from '@ant-design/icons'
import { userApi } from '../../api/user'
import { formatTime } from '../../utils/format'

const { Title, Text } = Typography

export default function UserManage() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [statusFilter, setStatusFilter] = useState(undefined)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const params = { page, page_size: pageSize }
      if (keyword) params.keyword = keyword
      if (statusFilter !== undefined && statusFilter !== null) {
        params.status = statusFilter
      }
      const res = await userApi.list(params)
      setData(res.items || [])
      setTotal(res.total || 0)
    } catch (e) {
      message.error(e.message || '加载用户列表失败')
    } finally {
      setLoading(false)
    }
  }, [page, pageSize, keyword, statusFilter])

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

  const handleDelete = async (userId) => {
    try {
      await userApi.delete(userId)
      message.success('已删除用户')
      loadData()
    } catch (e) {
      message.error(e.message || '删除失败')
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
      width: 100,
      render: (role) => (
        <Tag color={role === 'admin' ? 'purple' : 'default'}>
          {role === 'admin' ? '管理员' : '普通用户'}
        </Tag>
      ),
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
        <Button icon={<ReloadOutlined />} onClick={loadData}>
          刷新
        </Button>
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
          style={{ width: 140 }}
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
    </Card>
  )
}
