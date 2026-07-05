"""DashScope (通义千问) 适配器实现"""
import asyncio
from typing import AsyncGenerator

import dashscope

from common.logging_config import get_logger
from .base import LLMAdapter

logger = get_logger()

# 哨兵对象，用于标识流结束（避免 StopIteration 泄漏到异步生成器）
_STREAM_END = object()


class DashScopeAdapter(LLMAdapter):
    """基于阿里云 DashScope SDK 的 LLM 适配器"""

    def __init__(self, api_key: str, llm_model: str, embedding_model: str):
        self.api_key = api_key
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        # 设置全局 api_key 作为兜底
        if api_key:
            dashscope.api_key = api_key

    async def chat_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式对话：调用 dashscope.Generation.call(stream=True, incremental_output=True)
        逐 chunk yield 文本内容。

        dashscope SDK 的流式调用返回同步可迭代对象，这里通过 asyncio.to_thread
        在独立线程中逐次拉取 next()，避免阻塞事件循环，实现真正的流式输出。
        """
        model = kwargs.get("model", self.llm_model)

        def _make_iter():
            """创建 dashscope 流式响应迭代器"""
            return iter(
                dashscope.Generation.call(
                    model=model,
                    prompt=prompt,
                    api_key=self.api_key,
                    stream=True,
                    incremental_output=True,
                )
            )

        def _next_item(iterator):
            """安全地取下一个元素，遇 StopIteration 返回哨兵"""
            try:
                return next(iterator)
            except StopIteration:
                return _STREAM_END

        # 在线程中初始化迭代器（首次调用会建立连接）
        try:
            iterator = await asyncio.to_thread(_make_iter)
        except Exception as e:
            logger.error("DashScope chat_stream 初始化失败: %s", e)
            raise

        # 逐 chunk 在线程中拉取，每个 chunk 就绪即 yield
        while True:
            response = await asyncio.to_thread(_next_item, iterator)
            if response is _STREAM_END:
                break
            # 流式响应中每个 response.output.text 是文本片段
            text = getattr(getattr(response, "output", None), "text", None)
            if text:
                yield text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        文本向量化：调用 dashscope.TextEmbedding.call
        从 response.output.embeddings 提取向量列表。
        """
        if not texts:
            return []

        def _call_embed():
            response = dashscope.TextEmbedding.call(
                model=self.embedding_model,
                input=texts,
                api_key=self.api_key,
            )
            return response

        try:
            response = await asyncio.to_thread(_call_embed)
        except Exception as e:
            logger.error("DashScope embed 调用失败: %s", e)
            raise

        # response.output.embeddings 是列表，每个元素有 .embedding 字段
        # 兼容 dashscope SDK 不同版本：output 可能是对象或 dict
        output = getattr(response, "output", None)
        if isinstance(output, dict):
            embeddings_obj = output.get("embeddings")
        else:
            embeddings_obj = getattr(output, "embeddings", None)
        if not embeddings_obj:
            logger.error("DashScope embed 返回为空: %s", response)
            raise RuntimeError("向量化服务返回空结果")

        embeddings = []
        for item in embeddings_obj:
            # 兼容对象属性访问与字典访问
            if isinstance(item, dict):
                vec = item.get("embedding")
            else:
                vec = getattr(item, "embedding", None)
            if vec:
                embeddings.append(list(vec))

        if not embeddings:
            raise RuntimeError("未能从向量化响应中提取到向量")

        return embeddings
