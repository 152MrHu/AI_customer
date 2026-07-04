"""对话服务 Pydantic 数据模型"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


# ========== 请求模型 ==========

class CreateSessionRequest(BaseModel):
    """创建会话请求"""
    knowledge_base_id: Optional[int] = Field(
        None, description="知识库 ID，为 None 时使用默认知识库(kb_id=1)"
    )


class SendMessageRequest(BaseModel):
    """发送消息请求"""
    content: str = Field(
        ..., min_length=1, max_length=2000, description="消息内容(1-2000字符)"
    )


# ========== 响应模型 ==========

class MessageItem(BaseModel):
    """消息项"""
    message_id: int
    role: str
    content: str
    sources: Optional[List[dict]] = None
    created_at: Optional[str] = None


class SessionListItem(BaseModel):
    """会话列表项"""
    session_id: int
    title: str
    last_message_preview: Optional[str] = None
    updated_at: Optional[str] = None


class SessionDetail(BaseModel):
    """会话详情"""
    session_id: int
    title: str
    knowledge_base_id: Optional[int] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    messages: List[MessageItem] = Field(default_factory=list)


class CreateSessionResponse(BaseModel):
    """创建会话响应"""
    session_id: int
    title: str
    knowledge_base_id: int
    created_at: Optional[str] = None
