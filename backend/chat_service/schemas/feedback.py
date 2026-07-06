"""消息反馈 Pydantic 数据模型"""
from typing import Optional

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    """提交反馈请求"""
    rating: int = Field(
        ..., ge=0, le=1, description="评分: 1=赞, 0=踩"
    )
    comment: Optional[str] = Field(
        None, max_length=500, description="反馈备注（不超过500字符）"
    )
