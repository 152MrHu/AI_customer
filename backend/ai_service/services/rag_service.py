"""RAG 检索增强生成服务 - 完整链路异步生成器"""
import asyncio
from typing import AsyncGenerator

from common.config import settings
from common.logging_config import get_logger
from common.response import ErrorCode
from ..adapter.base import LLMAdapter
from ..retrieval.vector_store import VectorStore
from ..retrieval.prompt import build_prompt
from ..utils.sse import token_frame, sources_frame, done_frame, error_frame
from ..schemas.chat import RagChatRequest

logger = get_logger()


async def _aiter_with_overall_timeout(gen, timeout: float) -> AsyncGenerator:
    """
    带整体超时限制的异步生成器包装：
    记录截止时间，每次取下一个元素时用剩余时间作为 wait_for 超时。
    超时则抛出 asyncio.TimeoutError。
    """
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
    chroma_client,
    config=settings,
) -> AsyncGenerator[str, None]:
    """
    RAG 问答流程（异步生成器，逐帧 yield SSE 文本）：
    1. 检查知识库是否为空(count_collection)
    2. query 向量化 adapter.embed([query])
    3. ChromaDB 检索 top_k
    4. 过滤 score < SIMILARITY_THRESHOLD
    5. 拼 Prompt
    6. adapter.chat_stream(prompt) 逐 token yield SSE token 帧
    7. yield sources 帧
    8. yield done 帧
    异常时 yield error 帧(5001超时/5002不可用/5003空库)
    """
    kb_id = request.knowledge_base_id
    query = request.query
    top_k = request.top_k or config.TOP_K
    threshold = config.SIMILARITY_THRESHOLD

    vector_store = VectorStore(chroma_client)

    # 1. 检查知识库是否为空
    try:
        count = vector_store.count_collection(kb_id)
    except Exception as e:
        logger.error("知识库计数失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "知识库检索服务不可用")
        return

    if count == 0:
        logger.warning("知识库为空, kb_id=%s", kb_id)
        yield error_frame(ErrorCode.KB_EMPTY, "知识库为空，请先上传文档")
        return

    # 2. query 向量化（施加超时）
    try:
        embeddings = await asyncio.wait_for(
            adapter.embed([query]),
            timeout=config.AI_TIMEOUT,
        )
        query_embedding = embeddings[0]
    except asyncio.TimeoutError:
        logger.error("query 向量化超时, kb_id=%s", kb_id)
        yield error_frame(ErrorCode.AI_TIMEOUT, "AI服务向量化超时，请稍后重试")
        return
    except Exception as e:
        logger.error("query 向量化失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "AI服务向量化不可用")
        return

    # 3. ChromaDB 检索 top_k
    try:
        retrieved = vector_store.query(kb_id, query_embedding, top_k=top_k)
    except Exception as e:
        logger.error("ChromaDB 检索失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "知识库检索失败")
        return

    # 4. 过滤低相似度结果
    filtered = [item for item in retrieved if item.get("score", 0.0) >= threshold]
    logger.info("RAG 检索完成, kb_id=%s, 候选=%d, 过滤后=%d",
                kb_id, len(retrieved), len(filtered))

    # 准备 sources（用于前端展示）
    sources = [
        {
            "doc_name": item.get("doc_name", "未知文档"),
            "score": item.get("score", 0.0),
            "snippet": item.get("snippet", ""),
        }
        for item in filtered
    ]

    # 5. 拼 Prompt（过滤后为空仍调用 LLM，让它回答"暂无相关信息"）
    context_dicts = [msg.model_dump() for msg in request.context]
    prompt = build_prompt(filtered, context_dicts, query)

    # 6. 流式生成 token 帧（施加整体超时）
    try:
        stream = _aiter_with_overall_timeout(
            adapter.chat_stream(prompt), config.AI_TIMEOUT
        )
        async for token in stream:
            yield token_frame(token)
    except asyncio.TimeoutError:
        logger.error("LLM 流式生成超时, kb_id=%s", kb_id)
        yield error_frame(ErrorCode.AI_TIMEOUT, "AI服务生成超时，请稍后重试")
        return
    except Exception as e:
        logger.error("LLM 流式生成失败, kb_id=%s: %s", kb_id, e)
        yield error_frame(ErrorCode.AI_UNAVAILABLE, "AI服务生成不可用")
        return

    # 7. yield sources 帧
    yield sources_frame(sources)

    # 8. yield done 帧
    yield done_frame()
