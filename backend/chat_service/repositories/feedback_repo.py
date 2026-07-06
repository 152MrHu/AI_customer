"""消息反馈表数据访问层 - 纯 SQL 操作"""
from typing import Optional

from common.database import DB, fetchone


async def upsert_feedback(
    message_id: int,
    user_id: int,
    rating: int,
    comment: Optional[str] = None,
) -> None:
    """
    插入或更新反馈（赞/踩）。
    同一用户对同一条消息只能有一条反馈，重复提交则覆盖 rating 和 comment。
    """
    sql = (
        "INSERT INTO message_feedback (message_id, user_id, rating, comment) "
        "VALUES (%s, %s, %s, %s) "
        "ON DUPLICATE KEY UPDATE rating = VALUES(rating), comment = VALUES(comment)"
    )
    async with DB() as db:
        await db.execute(sql, (message_id, user_id, rating, comment))


async def get_user_feedback(
    message_id: int, user_id: int
) -> Optional[dict]:
    """查询当前用户对某条消息的反馈，返回 {rating, comment} 或 None"""
    sql = (
        "SELECT rating, comment FROM message_feedback "
        "WHERE message_id = %s AND user_id = %s"
    )
    return await fetchone(sql, (message_id, user_id))
