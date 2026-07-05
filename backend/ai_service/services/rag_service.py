"""RAG 检索增强生成服务 - 支持双模式异步生成器"""
import asyncio
from typing import AsyncGenerator

from common.config import settings
from common.logging_config import get_logger
from common.response import ErrorCode
from ..adapter.base import LLMAdapter
from ..retrieval.vector_store import VectorStore
from ..retrieval.prompt import build_prompt, build_messages
from ..utils.sse import token_frame, sources_frame, done_frame, error_frame
from ..schemas.chat import RagChatRequest

logger = get_logger()


async def _aiter_with_overall_timeout(gen, timeout: float) -> AsyncGenerator:
    """带整体超时限制的异步生成器包装"""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while True:
        remaining = deadline - loop.time()
        if remaining <= 0:
            raise asyncio.TimeoutError()
        try:
            item = await asyncio.wait_for(gen.__anext__(), timeout=remaining)
        except StopAsyncIteration:
            return
        yield item


async def rag_chat(
    request: RagChatRequest,
    adapter: LLMAdapter,
    config=settings,
) -> AsyncGenerator[str, None]:
    """
    双模式问答流程：
    - kb 模式：严格 RAG，知识库无相关内容则回答"抱歉，知识库中没有相关信息"
    - assistant 模式：通用助手 + 搜索增强（DashScope enable_search）
    """
    mode = request.mode
    kb_id = request.knowledge_base_id
    query = request.query

    # ===== assistant 模式：直接走 LLM（带搜索增强） =====
    if mode == "assistant":
        logger.info("通用助手模式: kb_id=%s, query=%s", kb_id, query[:50])
        context_dicts = [msg.model_dump() for msg in request.context]

        # 使用 messages 格式（system + 对话历史 + user 分离）
        # DashScope 的 enable_search 基于 user message 内容搜索，
        # 所以必须把用户问题单独作为 user message，而非嵌入长 prompt
        messages = build_messages([], context_dicts, query, mode="assistant")

        try:
            stream = _aiter_with_overall_timeout(
                adapter.chat_stream(messages=messages, enable_search=True),
                config.AI_TIMEOUT,
            )
            async for token in stream:
                yield token_frame(token)
        except asyncio.TimeoutError:
            yield error_frame(ErrorCode.AI_TIMEOUT, "AI服务生成超时，请稍后重试")
            return
        except Exception as e:
            logger.error("LLM 生成失败: %s", e)
            yield error_frame(ErrorCode.AI_UNAVAILABLE, "AI服务生成不可用")
            return

        yield sources_frame([])
        yield done_frame()
        return

    # ===== kb 模式：严格 RAG =====
    logger.info("知识库模式: kb_id=%s, query=%s", kb_id, query[:50])
    top_k = request.top_k or config.TOP_K
    threshold = config.SIMILARITY_THRESHOLD

    vector_store = VectorStore()

    # 1. 检查知识库是否为空
    try:
        count = await vector_store.count_collection(kb_id)
    except Exception as e:
        logger.error("知识库计数失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "知识库检索服务不可用")
        return

    if count == 0:
        # 知识库为空 → 严格回答"不知道"
        logger.warning("知识库为空, kb_id=%s", kb_id)
        yield token_frame("抱歉，当前知识库中暂无任何文档，无法回答您的问题。请先上传相关文档后再提问。")
        yield sources_frame([])
        yield done_frame()
        return

    # 2. query 向量化
    try:
        embeddings = await asyncio.wait_for(
            adapter.embed([query]),
            timeout=config.AI_TIMEOUT,
        )
        query_embedding = embeddings[0]
    except asyncio.TimeoutError:
        yield error_frame(ErrorCode.AI_TIMEOUT, "AI服务向量化超时，请稍后重试")
        return
    except Exception as e:
        logger.error("query 向量化失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "AI服务向量化不可用")
        return

    # 3. 远程向量检索
    try:
        retrieved = await vector_store.query(kb_id, query_embedding, top_k=top_k)
    except Exception as e:
        logger.error("远程检索失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "知识库检索失败")
        return

    # 4. 过滤低相似度结果
    filtered = [item for item in retrieved if item.get("score", 0.0) >= threshold]
    logger.info("RAG 检索完成, kb_id=%s, 候选=%d, 过滤后=%d",
                kb_id, len(retrieved), len(filtered))

    # 5. 准备 sources
    sources = [
        {
            "doc_name": item.get("doc_name", "未知文档"),
            "score": item.get("score", 0.0),
            "snippet": item.get("snippet", ""),
        }
        for item in filtered
    ]

    # 6. 拼 Prompt + 流式生成
    context_dicts = [msg.model_dump() for msg in request.context]
    prompt = build_prompt(filtered, context_dicts, query, mode="kb")

    try:
        stream = _aiter_with_overall_timeout(
            adapter.chat_stream(prompt), config.AI_TIMEOUT
        )
        async for token in stream:
            yield token_frame(token)
    except asyncio.TimeoutError:
        yield error_frame(ErrorCode.AI_TIMEOUT, "AI服务生成超时，请稍后重试")
        return
    except Exception as e:
        logger.error("LLM 流式生成失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "AI服务生成不可用")
        return

    # 7. yield sources + done
    yield sources_frame(sources)
    yield done_frame()
