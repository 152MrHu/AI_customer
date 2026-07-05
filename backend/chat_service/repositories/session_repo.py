"""会话表数据访问层 - 纯 SQL 操作"""
from typing import Optional

from common.database import DB, fetchone, fetchall, execute


async def insert_session(
    user_id: int, kb_id: Optional[int], title: str = "新会话", mode: str = "kb"
) -> int:
    """插入新会话，返回自增 session_id"""
    sql = (
        "INSERT INTO sessions (user_id, kb_id, title, mode) "
        "VALUES (%s, %s, %s, %s)"
    )
    async with DB() as db:
        await db.cur.execute(sql, (user_id, kb_id, title, mode))
        return db.cur.lastrowid


async def find_by_id(session_id: int) -> Optional[dict]:
    """按 session_id 查询（不限用户，仅用于内部判断）"""
    sql = "SELECT * FROM sessions WHERE session_id = %s LIMIT 1"
    return await fetchone(sql, (session_id,))


async def find_by_id_and_user(
    session_id: int, user_id: int
) -> Optional[dict]:
    """按 session_id + user_id 查询（校验会话归属）"""
    sql = (
        "SELECT * FROM sessions "
        "WHERE session_id = %s AND user_id = %s AND status = 1 "
        "LIMIT 1"
    )
    return await fetchone(sql, (session_id, user_id))


async def list_sessions(
    user_id: int,
    keyword: Optional[str],
    offset: int,
    limit: int,
) -> list[dict]:
    """分页查询用户会话列表，按 updated_at DESC，仅 status=1"""
    conditions = ["user_id = %s", "status = 1"]
    params: list = [user_id]
    if keyword:
        conditions.append("title LIKE %s")
        params.append(f"%{keyword}%")
    where = " WHERE " + " AND ".join(conditions)
    sql = (
        f"SELECT session_id, user_id, kb_id, title, mode, status, "
        f"created_at, updated_at "
        f"FROM sessions{where} "
        f"ORDER BY updated_at DESC LIMIT %s OFFSET %s"
    )
    params.extend([limit, offset])
    return await fetchall(sql, tuple(params))


async def count_sessions(user_id: int, keyword: Optional[str]) -> int:
    """统计用户会话总数"""
    conditions = ["user_id = %s", "status = 1"]
    params: list = [user_id]
    if keyword:
        conditions.append("title LIKE %s")
        params.append(f"%{keyword}%")
    where = " WHERE " + " AND ".join(conditions)
    sql = f"SELECT COUNT(*) AS cnt FROM sessions{where}"
    row = await fetchone(sql, tuple(params))
    return int(row["cnt"]) if row else 0


async def update_title(session_id: int, title: str) -> int:
    """更新会话标题"""
    sql = "UPDATE sessions SET title = %s WHERE session_id = %s"
    return await execute(sql, (title, session_id))


async def update_timestamp(session_id: int) -> int:
    """更新会话 updated_at 为当前时间"""
    sql = "UPDATE sessions SET updated_at = NOW() WHERE session_id = %s"
    return await execute(sql, (session_id,))


async def soft_delete(session_id: int) -> int:
    """软删除会话（status=0）"""
    sql = "UPDATE sessions SET status = 0 WHERE session_id = %s"
    return await execute(sql, (session_id,))


async def count_user_sessions(user_id: int) -> int:
    """统计用户的有效会话总数（用于上限检查）"""
    sql = (
        "SELECT COUNT(*) AS cnt FROM sessions "
        "WHERE user_id = %s AND status = 1"
    )
    row = await fetchone(sql, (user_id,))
    return int(row["cnt"]) if row else 0


async def find_oldest_session(user_id: int) -> Optional[dict]:
    """查询用户最早的有效会话（用于超出上限时清理）"""
    sql = (
        "SELECT session_id FROM sessions "
        "WHERE user_id = %s AND status = 1 "
        "ORDER BY updated_at ASC LIMIT 1"
    )
    return await fetchone(sql, (user_id,))
