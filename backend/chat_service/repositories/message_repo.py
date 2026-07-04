"""消息表数据访问层 - 纯 SQL 操作"""
from typing import Optional

from common.database import DB, fetchall, fetchone, execute


async def insert_message(
    session_id: int,
    role: str,
    content: str,
    sources: Optional[str] = None,
) -> int:
    """
    插入消息，返回自增 message_id
    :param sources: JSON 字符串或 None
    """
    sql = (
        "INSERT INTO messages (session_id, role, content, sources) "
        "VALUES (%s, %s, %s, %s)"
    )
    async with DB() as db:
        await db.cur.execute(sql, (session_id, role, content, sources))
        return db.cur.lastrowid


async def find_recent_context(
    session_id: int, limit: int = 20
) -> list[dict]:
    """
    查询最近 limit 条消息（约 10 轮对话），
    先按 created_at DESC 取，再反转为正序（便于拼 prompt）
    """
    sql = (
        "SELECT message_id, session_id, role, content, sources, created_at "
        "FROM messages WHERE session_id = %s "
        "ORDER BY created_at DESC LIMIT %s"
    )
    rows = await fetchall(sql, (session_id, limit))
    rows.reverse()
    return rows


async def find_by_session(session_id: int) -> list[dict]:
    """查询会话全部消息，按 created_at 正序"""
    sql = (
        "SELECT message_id, session_id, role, content, sources, created_at "
        "FROM messages WHERE session_id = %s "
        "ORDER BY created_at ASC"
    )
    return await fetchall(sql, (session_id,))


async def get_last_message_preview(session_id: int) -> Optional[str]:
    """获取最后一条消息 content 的前 50 字"""
    sql = (
        "SELECT content FROM messages WHERE session_id = %s "
        "ORDER BY created_at DESC LIMIT 1"
    )
    row = await fetchone(sql, (session_id,))
    if not row:
        return None
    content = row.get("content") or ""
    return content[:50] if content else None
