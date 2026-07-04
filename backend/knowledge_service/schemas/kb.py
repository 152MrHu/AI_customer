"""知识库相关数据模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CreateKbRequest(BaseModel):
    """创建知识库请求"""
    name: str = Field(..., max_length=50, description="知识库名称")
    description: Optional[str] = Field(None, max_length=200, description="知识库描述")


class KbResponse(BaseModel):
    """知识库详情响应"""
    kb_id: int
    name: str
    description: Optional[str] = None
    document_count: int
    created_at: datetime
    updated_at: datetime


class KbListItem(KbResponse):
    """知识库列表项（与 KbResponse 相同）"""
    pass
