"""用户数据访问层 - 纯 SQL 操作"""
from typing import Optional

from common.database import DB, fetchone, fetchall, execute


async def insert_user(
    username: str,
    phone: str,
    email: Optional[str],
    password_hash: str,
    role: str = "user",
) -> int:
    """插入新用户，返回自增 user_id"""
    sql = (
        "INSERT INTO users (username, phone, email, password_hash, role) "
        "VALUES (%s, %s, %s, %s, %s)"
    )
    async with DB() as db:
        await db.cur.execute(sql, (username, phone, email, password_hash, role))
        return db.cur.lastrowid


# 不含 password_hash 的安全列（用于常规查询）
_USER_SAFE_COLS = (
    "user_id, username, phone, email, role, status, created_at, last_login_at"
)


async def find_by_username(username: str) -> Optional[dict]:
    """按用户名查询（不含密码哈希）"""
    sql = f"SELECT {_USER_SAFE_COLS} FROM users WHERE username = %s LIMIT 1"
    return await fetchone(sql, (username,))


async def find_by_phone(phone: str) -> Optional[dict]:
    """按手机号查询（不含密码哈希）"""
    sql = f"SELECT {_USER_SAFE_COLS} FROM users WHERE phone = %s LIMIT 1"
    return await fetchone(sql, (phone,))


async def find_by_account(account: str) -> Optional[dict]:
    """按账号查询：先按 username，没有再按 phone（不含密码哈希）"""
    user = await find_by_username(account)
    if user:
        return user
    return await find_by_phone(account)


async def find_by_account_with_password(account: str) -> Optional[dict]:
    """按账号查询（含 password_hash，仅用于登录验证）"""
    user = await fetchone(
        "SELECT * FROM users WHERE username = %s LIMIT 1", (account,)
    )
    if user:
        return user
    return await fetchone(
        "SELECT * FROM users WHERE phone = %s LIMIT 1", (account,)
    )


async def find_by_id(user_id: int) -> Optional[dict]:
    """按 user_id 查询（不含密码哈希）"""
    sql = f"SELECT {_USER_SAFE_COLS} FROM users WHERE user_id = %s LIMIT 1"
    return await fetchone(sql, (user_id,))


async def find_by_id_with_password(user_id: int) -> Optional[dict]:
    """按 user_id 查询（含 password_hash，仅用于密码校验）"""
    sql = "SELECT * FROM users WHERE user_id = %s LIMIT 1"
    return await fetchone(sql, (user_id,))


async def update_profile(
    user_id: int,
    username: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
) -> int:
    """更新用户资料，仅更新不为 None 的字段"""
    fields = []
    params = []
    if username is not None:
        fields.append("username = %s")
        params.append(username)
    if phone is not None:
        fields.append("phone = %s")
        params.append(phone)
    if email is not None:
        fields.append("email = %s")
        params.append(email)
    if not fields:
        return 0
    sql = "UPDATE users SET " + ", ".join(fields) + " WHERE user_id = %s"
    params.append(user_id)
    return await execute(sql, tuple(params))


async def update_last_login(user_id: int) -> int:
    """更新最后登录时间为当前时间"""
    sql = "UPDATE users SET last_login_at = NOW() WHERE user_id = %s"
    return await execute(sql, (user_id,))


async def update_status(user_id: int, status: int) -> int:
    """更新用户状态"""
    sql = "UPDATE users SET status = %s WHERE user_id = %s"
    return await execute(sql, (status, user_id))


async def update_role(user_id: int, role: str) -> int:
    """更新用户角色"""
    sql = "UPDATE users SET role = %s WHERE user_id = %s"
    return await execute(sql, (role, user_id))


async def update_password(user_id: int, password_hash: str) -> int:
    """更新用户密码"""
    sql = "UPDATE users SET password_hash = %s WHERE user_id = %s"
    return await execute(sql, (password_hash, user_id))


async def soft_delete_user(user_id: int) -> int:
    """软删除用户（置 status=0）"""
    sql = "UPDATE users SET status = 0 WHERE user_id = %s"
    return await execute(sql, (user_id,))


def _build_where(
    keyword: Optional[str], status: Optional[int], role: Optional[str] = None
) -> tuple[str, list]:
    """构造公共 WHERE 子句与参数"""
    conditions: list[str] = []
    params: list = []
    if keyword:
        conditions.append("(username LIKE %s OR phone LIKE %s OR email LIKE %s)")
        like = f"%{keyword}%"
        params.extend([like, like, like])
    if status is not None:
        conditions.append("status = %s")
        params.append(status)
    if role is not None:
        conditions.append("role = %s")
        params.append(role)
    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


async def list_users(
    keyword: Optional[str],
    status: Optional[int],
    offset: int,
    limit: int,
    role: Optional[str] = None,
) -> list[dict]:
    """分页查询用户列表（不含 password_hash）"""
    where, params = _build_where(keyword, status, role)
    sql = (
        "SELECT user_id, username, phone, email, role, status, created_at "
        f"FROM users{where} "
        "ORDER BY created_at DESC LIMIT %s OFFSET %s"
    )
    params.extend([limit, offset])
    return await fetchall(sql, tuple(params))


async def count_users(
    keyword: Optional[str], status: Optional[int], role: Optional[str] = None
) -> int:
    """统计用户总数"""
    where, params = _build_where(keyword, status, role)
    sql = f"SELECT COUNT(*) AS cnt FROM users{where}"
    row = await fetchone(sql, tuple(params))
    return int(row["cnt"]) if row else 0
