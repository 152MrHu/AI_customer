"""AI 服务客户端 - 封装与 ai-service 的 SSE 交互"""
import json
from typing import AsyncGenerator, Optional

from common.config import settings
from common.http_client import stream_post
from common.logging_config import get_logger

logger = get_logger()


async def call_ai_chat(
    query: str,
    knowledge_base_id: int,
    context: list[dict],
    top_k: Optional[int] = None,
    mode: str = "kb",
) -> AsyncGenerator[str, None]:
    """
    调用 ai-service 的 /api/ai/chat 接口（SSE 流式），
    逐行 yield 原始 SSE 行文本。

    :param query: 用户问题
    :param knowledge_base_id: 知识库 ID
    :param context: 历史对话 [{"role": "user"/"assistant", "content": "..."}]
    :param top_k: 检索返回数量
    :param mode: 对话模式: kb=知识库模式, assistant=通用助手模式
    """
    url = f"{settings.AI_SERVICE_URL}/api/ai/chat"
    payload = {
        "query": query,
        "knowledge_base_id": knowledge_base_id,
        "context": context,
        "top_k": top_k or settings.TOP_K,
        "mode": mode,
    }
    logger.info(
        "调用 ai-service SSE 流: kb_id=%s, mode=%s, query_len=%s",
        knowledge_base_id, mode, len(query),
    )

    async for line in stream_post(url, json=payload):
        yield line


def parse_sse_line(line: str) -> Optional[dict]:
    """
    解析单行 SSE 文本，返回事件 dict 或 None（非数据行/解析失败）。
    输入格式: "data: {...}" 或空行
    """
    if not line:
        return None
    line = line.strip()
    if not line or not line.startswith("data:"):
        return None
    json_str = line[len("data:"):].strip()
    if not json_str:
        return None
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None
