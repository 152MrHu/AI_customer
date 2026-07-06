"""人工转接工单 Pydantic 数据模型"""
from typing import Optional

from pydantic import BaseModel, Field


class CreateHandoffRequest(BaseModel):
    """创建转接工单请求"""
    reason: Optional[str] = Field(
        None, max_length=500, description="转接原因（最多500字符）"
    )


class ResolveHandoffRequest(BaseModel):
    """解决转接工单请求"""
    resolution: str = Field(
        ..., max_length=1000, description="解决说明（最多1000字符）"
    )
