"""消息业务逻辑层 - 核心 SSE 流式问答"""
import json
from typing import AsyncGenerator

from common.logging_config import get_logger

from chat_service.repositories import session_repo, message_repo, handoff_repo
from chat_service.clients.ai_client import call_ai_chat, parse_sse_line
from common.sse import (
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

    # 基础安全检查：拒绝明显恶意内容
    if len(content) > 2000:
        yield error_frame(3002, "消息内容过长")
        return

    # 检测简单的重复字符攻击
    if len(set(content)) == 1 and len(content) > 50:
        yield error_frame(3002, "消息内容无效")
        return

    # 3. 保存用户消息
    await message_repo.insert_message(session_id, "user", content)

    # 4. 首条消息更新会话标题
    if session.get("title", "新会话") == "新会话":
        new_title = content.strip()[:20]
        await session_repo.update_title(session_id, new_title)

    # 5. 检查是否有活跃的人工客服工单（claimed 状态）
    #    如果有，跳过 AI，消息直接送达客服
    active_ticket = await handoff_repo.find_claimed_by_session(session_id)
    if active_ticket:
        logger.info("会话已有客服处理中，跳过AI: session_id=%s", session_id)
        yield token_frame("（已转接人工客服，您的消息已发送，请等待客服回复）")
        yield done_frame()
        return

    # 6. 加载最近 10 轮上下文
    context_rows = await message_repo.find_recent_context(session_id, 20)
    context = [
        {"role": r["role"], "content": r["content"]}
        for r in context_rows
    ]

    # 7. 调用 ai-service SSE 流式
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


async def send_agent_message(
    session_id: int, agent_id: int, content: str
) -> AsyncGenerator[str, None]:
    """
    客服发送消息：
    1. 校验会话存在
    2. 校验客服已认领该会话的转接工单
    3. 校验消息内容
    4. 保存消息（role=assistant）
    5. 返回 SSE token + done 帧
    """
    # 1. 校验会话存在
    session = await session_repo.find_by_id(session_id)
    if not session:
        yield error_frame(3001, "会话不存在")
        return

    # 2. 校验客服已认领该会话的转接工单
    ticket = await handoff_repo.find_claimed_by_session_and_user(session_id, agent_id)
    if not ticket:
        yield error_frame(403, "未认领该会话的转接工单或工单已处理")
        return

    # 3. 校验消息内容
    if not content or not content.strip():
        yield error_frame(3002, "消息内容为空")
        return

    if len(content) > 2000:
        yield error_frame(3002, "消息内容过长")
        return

    # 4. 保存消息（role=assistant）
    message_id = await message_repo.insert_message(session_id, "assistant", content)
    await session_repo.update_timestamp(session_id)

    # 5. 返回 SSE 帧
    yield token_frame(content)
    yield done_frame(message_id)
