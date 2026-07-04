"""LLM 适配层抽象基类"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator


class LLMAdapter(ABC):
    """大语言模型适配器抽象接口"""

    @abstractmethod
    async def chat_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式对话，逐 token yield 文本内容"""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本向量化，返回向量列表"""
        ...
