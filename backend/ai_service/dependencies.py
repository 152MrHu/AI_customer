"""依赖注入：提供全局 adapter 与 chroma_client"""
from typing import Optional

from .adapter.base import LLMAdapter


# 全局单例（在 main.py lifespan 中初始化）
_adapter: Optional[LLMAdapter] = None
_chroma_client = None


def set_adapter(adapter: LLMAdapter) -> None:
    """设置全局 adapter 实例（启动时调用）"""
    global _adapter
    _adapter = adapter


def set_chroma_client(client) -> None:
    """设置全局 chroma client（启动时调用）"""
    global _chroma_client
    _chroma_client = client


def get_adapter() -> LLMAdapter:
    """返回全局 adapter 实例"""
    if _adapter is None:
        raise RuntimeError("LLM adapter 尚未初始化")
    return _adapter


def get_chroma_client():
    """返回全局 chroma client"""
    if _chroma_client is None:
        raise RuntimeError("ChromaDB client 尚未初始化")
    return _chroma_client
