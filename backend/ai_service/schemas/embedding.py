"""文本向量化相关数据模型"""
from typing import List
from pydantic import BaseModel, Field


class EmbeddingRequest(BaseModel):
    """向量化请求"""
    texts: List[str] = Field(..., min_length=1, description="待向量化的文本列表")
    kb_id: int = Field(..., description="知识库 ID")


class EmbeddingResponse(BaseModel):
    """向量化响应"""
    embeddings: List[List[float]] = Field(..., description="向量列表")
    model: str = Field(..., description="使用的模型名称")
    dimensions: int = Field(..., description="向量维度")
