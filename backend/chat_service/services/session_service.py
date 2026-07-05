"""会话业务逻辑层"""
import json
from datetime import datetime
from typing import Optional

from common.exceptions import BusinessError
from common.response import ErrorCode
from common.pagination import PageParams
from common.redis_client import (
    cache_session,
    delete_cached_session,
)
from common.logging_config import setup_logger

from chat_service.schemas.session import CreateSessionRequest
from chat_service.repositories import session_repo, message_repo

logger = setup_logger("chat_service")

# 默认知识库 ID
DEFAULT_KB_ID = 1
# 用户会话上限
MAX_SESSIONS_PER_USER = 100


def _iso(dt) -> Optional[str]:
    """将 datetime 转为 ISO 字符串"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _parse_sources(sources_raw) -> Optional[list]:
    """将 sources 字段（JSON 字符串 / dict / None）统一转为 list 或 None"""
    if sources_raw is None:
        return None
    if isinstance(sources_raw, (list, dict)):
        return sources_raw if isinstance(sources_raw, list) else [sources_raw]
    if isinstance(sources_raw, (bytes, bytearray)):
        sources_raw = sources_raw.decode("utf-8", errors="ignore")
    if isinstance(sources_raw, str):
        if not sources_raw.strip():
            return None
        try:
            return json.loads(sources_raw)
        except (json.JSONDecodeError, ValueError):
            return None
    return None


def _to_message_item(row: dict) -> dict:
    """构造消息项"""
    return {
        "message_id": row["message_id"],
        "role": row["role"],
        "content": row["content"],
        "sources": _parse_sources(row.get("sources")),
        "created_at": _iso(row.get("created_at")),
    }


def _to_session_detail(row: dict, messages: list[dict]) -> dict:
    """构造会话详情"""
    return {
        "session_id": row["session_id"],
        "title": row.get("title", "新会话"),
        "knowledge_base_id": row.get("kb_id"),
        "mode": row.get("mode", "kb"),
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "messages": [_to_message_item(m) for m in messages],
    }


async def create_session(user_id: int, data: CreateSessionRequest) -> dict:
    """
    创建会话：
    - kb_id 为 None 时使用默认知识库(1)
    - mode: kb=知识库模式, assistant=通用助手模式
    - 检查用户会话上限(100)，超过自动清理最早已删除前的最早会话
    - 创建 session 并写 Redis 缓存
    """
    kb_id = data.knowledge_base_id if data.knowledge_base_id else DEFAULT_KB_ID
    mode = data.mode if data.mode in ("kb", "assistant") else "kb"

    # 检查会话数量上限，超过则清理最早的会话
    current_count = await session_repo.count_user_sessions(user_id)
    if current_count >= MAX_SESSIONS_PER_USER:
        oldest = await session_repo.find_oldest_session(user_id)
        if oldest:
            logger.info(
                "用户会话数达上限，清理最早会话: user_id=%s, session_id=%s",
                user_id, oldest["session_id"],
            )
            await session_repo.soft_delete(oldest["session_id"])
            await delete_cached_session(oldest["session_id"])

    # 创建新会话
    session_id = await session_repo.insert_session(user_id, kb_id, "新会话", mode=mode)
    session = await session_repo.find_by_id(session_id)
    if not session:
        raise BusinessError(ErrorCode.SERVER_ERROR, "会话创建失败")

    # 写入 Redis 缓存
    cache_data = {
        "session_id": str(session_id),
        "user_id": str(user_id),
        "kb_id": str(kb_id),
        "mode": mode,
        "title": session.get("title", "新会话"),
    }
    try:
        await cache_session(session_id, cache_data)
    except Exception as e:
        logger.warning("写会话缓存失败(忽略): session_id=%s, err=%s", session_id, e)

    logger.info(
        "创建会话成功: user_id=%s, session_id=%s, kb_id=%s, mode=%s",
        user_id, session_id, kb_id, mode,
    )
    return {
        "session_id": session_id,
        "title": session.get("title", "新会话"),
        "knowledge_base_id": kb_id,
        "mode": mode,
        "created_at": _iso(session.get("created_at")),
    }


async def list_sessions(
    user_id: int, keyword: Optional[str], page_params: PageParams
) -> dict:
    """分页查询会话列表，每条带 last_message_preview"""
    items_rows = await session_repo.list_sessions(
        user_id, keyword, page_params.offset, page_params.limit
    )
    total = await session_repo.count_sessions(user_id, keyword)

    items = []
    for row in items_rows:
        preview = await message_repo.get_last_message_preview(row["session_id"])
        items.append({
            "session_id": row["session_id"],
            "title": row.get("title", "新会话"),
            "mode": row.get("mode", "kb"),
            "last_message_preview": preview,
            "updated_at": _iso(row.get("updated_at")),
        })

    return {
        "total": total,
        "page": page_params.page,
        "page_size": page_params.page_size,
        "items": items,
    }


async def get_session_detail(session_id: int, user_id: int) -> dict:
    """获取会话详情，校验归属(3001)"""
    session = await session_repo.find_by_id_and_user(session_id, user_id)
    if not session:
        raise BusinessError(ErrorCode.SESSION_NOT_FOUND, "会话不存在")

    messages = await message_repo.find_by_session(session_id)
    return _to_session_detail(session, messages)


async def delete_session(session_id: int, user_id: int) -> None:
    """删除会话（软删除），校验归属(3001)，清缓存"""
    session = await session_repo.find_by_id_and_user(session_id, user_id)
    if not session:
        raise BusinessError(ErrorCode.SESSION_NOT_FOUND, "会话不存在")

    await session_repo.soft_delete(session_id)
    try:
        await delete_cached_session(session_id)
    except Exception as e:
        logger.warning("清会话缓存失败(忽略): session_id=%s, err=%s", session_id, e)

    logger.info("删除会话成功: user_id=%s, session_id=%s", user_id, session_id)
