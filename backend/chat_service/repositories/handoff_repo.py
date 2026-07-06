"""人工转接工单数据访问层 - 纯 SQL 操作"""
from typing import Optional

from common.database import DB, fetchone, fetchall, execute


async def create_ticket(
    session_id: int, user_id: int, reason: Optional[str] = None
) -> int:
    """创建转接工单，返回自增 ticket_id"""
    sql = (
        "INSERT INTO handoff_tickets (session_id, user_id, reason) "
        "VALUES (%s, %s, %s)"
    )
    async with DB() as db:
        await db.cur.execute(sql, (session_id, user_id, reason))
        return db.cur.lastrowid


async def find_by_id(ticket_id: int) -> Optional[dict]:
    """按 ticket_id 查询工单（含用户名）"""
    sql = (
        "SELECT h.*, u.username FROM handoff_tickets h "
        "LEFT JOIN users u ON h.user_id = u.user_id "
        "WHERE h.ticket_id = %s LIMIT 1"
    )
    return await fetchone(sql, (ticket_id,))


async def list_tickets(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    claimed_by: Optional[int] = None,
    offset: int = 0,
    limit: int = 20,
) -> list[dict]:
    """分页查询工单列表"""
    conditions: list[str] = []
    params: list = []
    if user_id is not None:
        conditions.append("h.user_id = %s")
        params.append(user_id)
    if status:
        # 支持逗号分隔的多状态：pending,claimed → IN ('pending','claimed')
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            conditions.append("h.status = %s")
            params.append(statuses[0])
        else:
            placeholders = ",".join(["%s"] * len(statuses))
            conditions.append(f"h.status IN ({placeholders})")
            params.extend(statuses)
    if claimed_by is not None:
        conditions.append("h.claimed_by = %s")
        params.append(claimed_by)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = (
        "SELECT h.*, u.username FROM handoff_tickets h "
        "LEFT JOIN users u ON h.user_id = u.user_id"
        f"{where} "
        "ORDER BY h.created_at DESC LIMIT %s OFFSET %s"
    )
    params.extend([limit, offset])
    return await fetchall(sql, tuple(params))


async def count_tickets(
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    claimed_by: Optional[int] = None,
) -> int:
    """统计工单总数"""
    conditions: list[str] = []
    params: list = []
    if user_id is not None:
        conditions.append("h.user_id = %s")
        params.append(user_id)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if len(statuses) == 1:
            conditions.append("h.status = %s")
            params.append(statuses[0])
        else:
            placeholders = ",".join(["%s"] * len(statuses))
            conditions.append(f"h.status IN ({placeholders})")
            params.extend(statuses)
    if claimed_by is not None:
        conditions.append("h.claimed_by = %s")
        params.append(claimed_by)
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    sql = f"SELECT COUNT(*) AS cnt FROM handoff_tickets h{where}"
    row = await fetchone(sql, tuple(params))
    return int(row["cnt"]) if row else 0


async def claim_ticket(ticket_id: int, admin_id: int) -> int:
    """认领工单（管理员），仅 pending 状态可认领"""
    sql = (
        "UPDATE handoff_tickets SET status = 'claimed', claimed_by = %s "
        "WHERE ticket_id = %s AND status = 'pending'"
    )
    return await execute(sql, (admin_id, ticket_id))


async def resolve_ticket(ticket_id: int, resolution: str) -> int:
    """解决工单，仅 claimed 状态可解决"""
    sql = (
        "UPDATE handoff_tickets SET status = 'resolved', resolution = %s "
        "WHERE ticket_id = %s AND status = 'claimed'"
    )
    return await execute(sql, (resolution, ticket_id))


async def close_ticket(ticket_id: int) -> int:
    """关闭工单（用户），仅 resolved 状态可关闭"""
    sql = (
        "UPDATE handoff_tickets SET status = 'closed' "
        "WHERE ticket_id = %s AND status = 'resolved'"
    )
    return await execute(sql, (ticket_id,))


async def find_claimed_by_session(session_id: int) -> Optional[dict]:
    """查询某会话当前是否有客服正在处理（claimed 状态）"""
    sql = (
        "SELECT * FROM handoff_tickets "
        "WHERE session_id = %s AND status = 'claimed' "
        "LIMIT 1"
    )
    return await fetchone(sql, (session_id,))


async def get_pending_count() -> int:
    """统计待处理工单数量"""
    sql = "SELECT COUNT(*) AS cnt FROM handoff_tickets WHERE status = 'pending'"
    row = await fetchone(sql)
    return int(row["cnt"]) if row else 0


async def find_claimed_by_session_and_user(session_id: int, claimed_by: int) -> Optional[dict]:
    """查询某用户认领的某会话的工单（claimed 状态）"""
    sql = (
        "SELECT * FROM handoff_tickets "
        "WHERE session_id = %s AND claimed_by = %s AND status = 'claimed' "
        "LIMIT 1"
    )
    return await fetchone(sql, (session_id, claimed_by))
