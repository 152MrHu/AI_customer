"""DashScope (通义千问) 适配器实现"""
import asyncio
from typing import AsyncGenerator

import dashscope

from common.logging_config import get_logger
from .base import LLMAdapter

logger = get_logger()

# 哨兵对象，用于标识流结束
_STREAM_END = object()

# 搜索增强推荐使用的模型（qwen-turbo 不支持联网搜索）
SEARCH_MODEL = "qwen-plus"


def _extract_text_prompt_format(response) -> str | None:
    """从 prompt 格式的流式响应中提取文本片段"""
    text = getattr(getattr(response, "output", None), "text", None)
    return text if text else None


def _extract_text_message_format(response) -> str | None:
    """从 messages 格式的流式响应中提取文本片段（兼容 dict/object）"""
    output = getattr(response, "output", None)
    if isinstance(output, dict):
        choices = output.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            return content if content else None
    else:
        choices = getattr(output, "choices", None)
        if choices:
            message = getattr(choices[0], "message", None)
            content = getattr(message, "content", None)
            return content if content else None
    # 旧格式兼容
    text = getattr(output, "text", None) if output else None
    return text if text else None


class DashScopeAdapter(LLMAdapter):
    """基于阿里云 DashScope SDK 的 LLM 适配器"""

    def __init__(self, api_key: str, llm_model: str, embedding_model: str):
        self.api_key = api_key
        self.llm_model = llm_model
        self.embedding_model = embedding_model
        if api_key:
            dashscope.api_key = api_key

    async def chat_stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        流式对话，逐 chunk yield 文本内容。

        kwargs:
        - model: 指定模型（默认 self.llm_model）
        - enable_search: True → 开启联网搜索增强，使用 qwen-plus + messages 格式
        """
        enable_search = kwargs.get("enable_search", False)

        if enable_search:
            # 联网搜索模式：使用 messages 格式 + enable_search=True
            model = kwargs.get("model", SEARCH_MODEL)
            call_kwargs = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "api_key": self.api_key,
                "stream": True,
                "incremental_output": True,
                "result_format": "message",
                "enable_search": True,
                "search_options": {
                    "search_strategy": "max",
                    "enable_source": True,
                },
            }
            extract_fn = _extract_text_message_format
        else:
            # 普通模式：使用 prompt 格式
            model = kwargs.get("model", self.llm_model)
            call_kwargs = {
                "model": model,
                "prompt": prompt,
                "api_key": self.api_key,
                "stream": True,
                "incremental_output": True,
            }
            extract_fn = _extract_text_prompt_format

        def _make_iter():
            return iter(dashscope.Generation.call(**call_kwargs))

        def _next_item(iterator):
            try:
                return next(iterator)
            except StopIteration:
                return _STREAM_END

        try:
            iterator = await asyncio.to_thread(_make_iter)
        except Exception as e:
            logger.error("DashScope chat_stream 初始化失败: %s", e)
            raise

        while True:
            response = await asyncio.to_thread(_next_item, iterator)
            if response is _STREAM_END:
                break
            text = extract_fn(response)
            if text:
                yield text

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """文本向量化"""
        if not texts:
            return []

        def _call_embed():
            return dashscope.TextEmbedding.call(
                model=self.embedding_model,
                input=texts,
                api_key=self.api_key,
            )

        try:
            response = await asyncio.to_thread(_call_embed)
        except Exception as e:
            logger.error("DashScope embed 调用失败: %s", e)
            raise

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
            if isinstance(item, dict):
                vec = item.get("embedding")
            else:
                vec = getattr(item, "embedding", None)
            if vec:
                embeddings.append(list(vec))

        if not embeddings:
            raise RuntimeError("未能从向量化响应中提取到向量")

        return embeddings
