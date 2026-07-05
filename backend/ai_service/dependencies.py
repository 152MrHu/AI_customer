"""依赖注入：提供全局 adapter"""
from typing import Optional

from .adapter.base import LLMAdapter


# 全局单例（在 main.py lifespan 中初始化）
_adapter: Optional[LLMAdapter] = None


def set_adapter(adapter: LLMAdapter) -> None:
    """设置全局 adapter 实例（启动时调用）"""
    global _adapter
    _adapter = adapter


def get_adapter() -> LLMAdapter:
    """返回全局 adapter 实例"""
    if _adapter is None:
        raise RuntimeError("LLM adapter 尚未初始化")
    return _adapter
