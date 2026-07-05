"""消息业务逻辑层 - 核心 SSE 流式问答"""
import json
from typing import AsyncGenerator

from common.logging_config import get_logger

from chat_service.repositories import session_repo, message_repo
from chat_service.clients.ai_client import call_ai_chat, parse_sse_line
from chat_service.clients.sse import (
    token_frame,
    sources_frame,
    done_frame,
    error_frame,
)

logger = get_logger()


async def send_message(
    session_id: int, user_id: int, content: str
) -> AsyncGenerator[str, None]:
    """
    发送消息，SSE 流式返回：
    1. 校验会话归属
    2. 校验消息内容
    3. 保存用户消息
    4. 首条消息更新会话标题
    5. 加载最近 10 轮上下文
    6. 调用 ai-service SSE 流式，透传 token / sources / done / error 帧
    7. done 时保存 AI 回答；error 时保存兜底提示
    """
    # 1. 校验会话归属
    session = await session_repo.find_by_id_and_user(session_id, user_id)
    if not session:
        yield error_frame(3001, "会话不存在")
        return

    # 2. 校验消息内容
    if not content or not content.strip():
        yield error_frame(3002, "消息内容为空")
        return

    # 3. 保存用户消息
    await message_repo.insert_message(session_id, "user", content)

    # 4. 首条消息更新会话标题
    if session.get("title", "新会话") == "新会话":
        new_title = content.strip()[:20]
        await session_repo.update_title(session_id, new_title)

    # 5. 加载最近 10 轮上下文
    context_rows = await message_repo.find_recent_context(session_id, 20)
    context = [
        {"role": r["role"], "content": r["content"]}
        for r in context_rows
    ]

    # 6. 调用 ai-service SSE 流式
    kb_id = session.get("kb_id") or 1
    mode = session.get("mode", "kb")
    full_response = ""
    sources_data = None

    try:
        async for line in call_ai_chat(content, kb_id, context, mode=mode):
            event = parse_sse_line(line)
            if event is None:
                continue

            event_type = event.get("type")

            if event_type == "token":
                token = event.get("content", "")
                full_response += token
                yield token_frame(token)

            elif event_type == "sources":
                sources_data = event.get("sources", [])
                yield sources_frame(sources_data)

            elif event_type == "done":
                # 保存 AI 回答
                sources_str = (
                    json.dumps(sources_data, ensure_ascii=False)
                    if sources_data else None
                )
                message_id = await message_repo.insert_message(
                    session_id, "assistant", full_response, sources=sources_str
                )
                await session_repo.update_timestamp(session_id)
                yield done_frame(message_id)

            elif event_type == "error":
                # AI 服务异常，但用户消息已保存，保存一条兜底提示
                error_msg = "AI服务暂时不可用，请稍后重试"
                await message_repo.insert_message(session_id, "assistant", error_msg)
                yield error_frame(
                    event.get("code", 5002),
                    event.get("message", "AI服务异常"),
                )

    except Exception as e:
        # 网络或解析异常：保存兜底提示并返回错误帧
        logger.exception(
            "调用 ai-service 异常: session_id=%s, err=%s", session_id, e
        )
        if full_response:
            # 已收到部分内容，保存部分回答
            await message_repo.insert_message(
                session_id, "assistant", full_response
            )
        else:
            await message_repo.insert_message(
                session_id, "assistant", "AI服务暂时不可用，请稍后重试"
            )
        await session_repo.update_timestamp(session_id)
        yield error_frame(5002, "AI服务暂时不可用，请稍后重试")
