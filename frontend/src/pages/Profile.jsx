import React, { useEffect, useState } from 'react'
import { Card, Form, Input, Button, message, Typography, Divider, Space, theme } from 'antd'
import { UserOutlined, LockOutlined, SaveOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import MainLayout from '../layouts/MainLayout'
import { userApi } from '../api/user'
import { useAuth } from '../context/AuthContext'

const { Title } = Typography

export default function Profile() {
  const { user, refreshUser } = useAuth()
  const navigate = useNavigate()
  const [profileForm] = Form.useForm()
  const [passwordForm] = Form.useForm()
  const [profileLoading, setProfileLoading] = useState(false)
  const [passwordLoading, setPasswordLoading] = useState(false)
  const { token: themeToken } = theme.useToken()

  useEffect(() => {
    if (user) {
      profileForm.setFieldsValue({
        username: user.username || '',
        phone: user.phone || '',
        email: user.email || '',
      })
    }
  }, [user, profileForm])

  const handleUpdateProfile = async (values) => {
    setProfileLoading(true)
    try {
      await userApi.updateProfile(values)
      message.success('个人信息更新成功')
      await refreshUser()
    } catch (e) {
      message.error(e.message || '更新个人信息失败')
    } finally {
      setProfileLoading(false)
    }
  }

  const handleChangePassword = async (values) => {
    setPasswordLoading(true)
    try {
      await userApi.changePassword({
        old_password: values.old_password,
        new_password: values.new_password,
      })
      message.success('密码修改成功')
      passwordForm.resetFields()
    } catch (e) {
      message.error(e.message || '修改密码失败')
    } finally {
      setPasswordLoading(false)
    }
  }

  return (
    <MainLayout>
      <div
        style={{
          maxWidth: 600,
          margin: '0 auto',
          padding: '32px 24px',
        }}
      >
        <Space style={{ marginBottom: 24 }}>
          <Button
            type="text"
            icon={<ArrowLeftOutlined />}
            onClick={() => navigate('/chat')}
          />
          <Title level={4} style={{ margin: 0 }}>
            个人中心
          </Title>
        </Space>

        {/* 个人信息 */}
        <Card
          title={
            <Space>
              <UserOutlined />
              <span>个人信息</span>
            </Space>
          }
          style={{ marginBottom: 24 }}
        >
          <Form
            form={profileForm}
            layout="vertical"
            onFinish={handleUpdateProfile}
          >
            <Form.Item
              name="username"
              label="用户名"
              rules={[{ required: true, message: '请输入用户名' }]}
            >
              <Input placeholder="请输入用户名" />
            </Form.Item>
            <Form.Item
              name="phone"
              label="手机号"
              rules={[
                { pattern: /^1\d{10}$/, message: '请输入正确的手机号格式' },
              ]}
            >
              <Input placeholder="请输入手机号" />
            </Form.Item>
            <Form.Item
              name="email"
              label="邮箱"
              rules={[{ type: 'email', message: '请输入正确的邮箱格式' }]}
            >
              <Input placeholder="请输入邮箱" />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={profileLoading}
                icon={<SaveOutlined />}
              >
                保存修改
              </Button>
            </Form.Item>
          </Form>
        </Card>

        {/* 修改密码 */}
        <Card
          title={
            <Space>
              <LockOutlined />
              <span>修改密码</span>
            </Space>
          }
        >
          <Form
            form={passwordForm}
            layout="vertical"
            onFinish={handleChangePassword}
          >
            <Form.Item
              name="old_password"
              label="原密码"
              rules={[{ required: true, message: '请输入原密码' }]}
            >
              <Input.Password placeholder="请输入原密码" />
            </Form.Item>
            <Form.Item
              name="new_password"
              label="新密码"
              rules={[
                { required: true, message: '请输入新密码' },
                { min: 6, message: '密码长度不能小于6位' },
              ]}
            >
              <Input.Password placeholder="请输入新密码" />
            </Form.Item>
            <Form.Item
              name="confirm_password"
              label="确认新密码"
              dependencies={['new_password']}
              rules={[
                { required: true, message: '请再次输入新密码' },
                ({ getFieldValue }) => ({
                  validator(_, value) {
                    if (!value || getFieldValue('new_password') === value) {
                      return Promise.resolve()
                    }
                    return Promise.reject(new Error('两次输入的密码不一致'))
                  },
                }),
              ]}
            >
              <Input.Password placeholder="请再次输入新密码" />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                loading={passwordLoading}
                icon={<SaveOutlined />}
              >
                修改密码
              </Button>
            </Form.Item>
          </Form>
        </Card>
      </div>
    </MainLayout>
  )
}
