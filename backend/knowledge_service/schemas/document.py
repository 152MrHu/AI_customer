"""文档相关数据模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DocumentResponse(BaseModel):
    """文档详情响应"""
    document_id: int
    kb_id: int
    file_name: str
    file_type: str
    file_size: int
    status: str  # pending / ready / failed
    chunk_count: int
    created_at: datetime
    processed_at: Optional[datetime] = None
