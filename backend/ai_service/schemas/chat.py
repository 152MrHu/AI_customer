"""聊天相关数据模型"""
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """单条对话消息"""
    role: str = Field(..., description="消息角色: user / assistant")
    content: str = Field(..., description="消息内容")


class RagChatRequest(BaseModel):
    """RAG 问答请求"""
    query: str = Field(..., min_length=1, description="用户问题")
    knowledge_base_id: int = Field(..., description="知识库 ID")
    context: List[ChatMessage] = Field(default_factory=list, description="对话历史")
    top_k: int = Field(default=5, ge=1, le=20, description="检索返回数量")


class SourceItem(BaseModel):
    """检索来源信息"""
    doc_name: str = Field(..., description="文档名称")
    score: float = Field(..., description="相似度得分")
    snippet: str = Field(..., description="命中文本片段")
