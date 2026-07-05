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

    async def chat_stream(
        self,
        prompt: str = None,
        messages: list = None,
        **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        流式对话，逐 chunk yield 文本内容。

        参数二选一：
        - prompt: 单条文本 prompt（普通模式，使用 prompt 格式调用）
        - messages: 消息列表 [{"role": "system/user/assistant", "content": "..."}]
                     （联网搜索模式必须用此格式，enable_search 基于 user message 搜索）

        kwargs:
        - model: 指定模型（默认 self.llm_model 或 SEARCH_MODEL）
        - enable_search: True → 开启联网搜索增强
        """
        enable_search = kwargs.get("enable_search", False)

        if enable_search:
            # 联网搜索模式：必须使用 messages 格式 + enable_search=True
            # DashScope 的搜索基于最后一条 user message 的内容，所以必须 system/user 分离
            model = kwargs.get("model", SEARCH_MODEL)
            call_messages = messages or [
                {"role": "user", "content": prompt or ""},
            ]
            call_kwargs = {
                "model": model,
                "messages": call_messages,
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
            # 普通模式：支持 prompt 或 messages 格式
            model = kwargs.get("model", self.llm_model)
            if messages:
                call_kwargs = {
                    "model": model,
                    "messages": messages,
                    "api_key": self.api_key,
                    "stream": True,
                    "incremental_output": True,
                    "result_format": "message",
                }
                extract_fn = _extract_text_message_format
            else:
                call_kwargs = {
                    "model": model,
                    "prompt": prompt or "",
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
        """文本向量化（自动分批，DashScope 限制每批最多 25 条）"""
        if not texts:
            return []

        # DashScope text-embedding-v3 单次请求最多 25 条文本
        BATCH_SIZE = 25

        all_embeddings = []
        for batch_start in range(0, len(texts), BATCH_SIZE):
            batch = texts[batch_start:batch_start + BATCH_SIZE]
            logger.debug("Embedding 分批: %d/%d, 本批 %d 条",
                         batch_start // BATCH_SIZE + 1,
                         (len(texts) + BATCH_SIZE - 1) // BATCH_SIZE,
                         len(batch))

            def _call_embed(batch_texts=batch):
                return dashscope.TextEmbedding.call(
                    model=self.embedding_model,
                    input=batch_texts,
                    api_key=self.api_key,
                )

            try:
                response = await asyncio.to_thread(_call_embed)
            except Exception as e:
                logger.error("DashScope embed 调用失败(批次%d): %s",
                             batch_start // BATCH_SIZE + 1, e)
                raise

            output = getattr(response, "output", None)
            if isinstance(output, dict):
                embeddings_obj = output.get("embeddings")
            else:
                embeddings_obj = getattr(output, "embeddings", None)
            if not embeddings_obj:
                logger.error("DashScope embed 返回为空(批次%d): %s",
                             batch_start // BATCH_SIZE + 1, response)
                raise RuntimeError(f"向量化服务返回空结果(批次{batch_start // BATCH_SIZE + 1})")

            for item in embeddings_obj:
                if isinstance(item, dict):
                    vec = item.get("embedding")
                else:
                    vec = getattr(item, "embedding", None)
                if vec:
                    all_embeddings.append(list(vec))

        if not all_embeddings:
            raise RuntimeError("未能从向量化响应中提取到向量")

        return all_embeddings
