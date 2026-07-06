"""用户业务逻辑层"""
from datetime import datetime, timezone
from typing import Optional

from common.security import hash_password, verify_password
from common.jwt_utils import create_token, decode_token, get_token_ttl_seconds
from common.redis_client import (
    blacklist_token,
    incr_login_fail,
    get_login_fail_count,
    clear_login_fail,
    incr_with_ttl,
    get_count,
)
from common.exceptions import BusinessError
from common.response import ErrorCode
from common.pagination import PageParams
from common.logging_config import setup_logger

from user_service.schemas.user import (
    RegisterRequest, LoginRequest, UpdateProfileRequest,
    ChangePasswordRequest, CreateAgentRequest, UpdateRoleRequest,
)
from user_service.repositories import user_repo

logger = setup_logger("user_service")

# 登录失败锁定阈值
MAX_LOGIN_FAIL = 5
# 自助重置密码限流：每 IP 每小时最多 3 次
SELF_RESET_RATE_LIMIT = 3
SELF_RESET_RATE_WINDOW = 3600


def _iso(dt) -> Optional[str]:
    """将 datetime 转为 ISO 字符串"""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _to_user_response(row: dict) -> dict:
    """构造用户详情响应（不含 password_hash）"""
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "phone": row["phone"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
        "created_at": _iso(row.get("created_at")),
        "last_login_at": _iso(row.get("last_login_at")),
    }


def _to_user_list_item(row: dict) -> dict:
    """构造用户列表项"""
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "phone": row["phone"],
        "email": row["email"],
        "role": row["role"],
        "status": row["status"],
        "created_at": _iso(row.get("created_at")),
    }


async def register(data: RegisterRequest) -> dict:
    """用户注册：校验唯一性 -> 加密密码 -> 插入"""
    # 用户名唯一性校验
    if await user_repo.find_by_username(data.username):
        raise BusinessError(ErrorCode.ACCOUNT_EXISTS, "用户名已存在")
    # 手机号唯一性校验
    if await user_repo.find_by_phone(data.phone):
        raise BusinessError(ErrorCode.ACCOUNT_EXISTS, "手机号已存在")

    pwd_hash = hash_password(data.password)
    user_id = await user_repo.insert_user(
        data.username, data.phone, data.email, pwd_hash
    )
    logger.info("用户注册成功: user_id=%s, username=%s", user_id, data.username)
    return {"user_id": user_id, "username": data.username}


async def login(data: LoginRequest) -> dict:
    """用户登录：查账号 -> 校验状态 -> 校验锁定 -> 校验密码 -> 签发 JWT"""
    account = data.account

    # 先用不含密码的查询确认用户是否存在（避免泄露密码哈希）
    user_safe = await user_repo.find_by_account(account)
    if not user_safe:
        raise BusinessError(
            ErrorCode.ACCOUNT_OR_PASSWORD_ERROR, "账号或密码错误"
        )

    user_id = user_safe["user_id"]

    # 账号状态校验
    if user_safe["status"] == 0:
        raise BusinessError(ErrorCode.ACCOUNT_DISABLED, "账号已禁用")

    # 登录失败次数校验（按 user_id 追踪，防止用用户名/手机号交替绕过锁定）
    fail_count = await get_login_fail_count(user_id)
    if fail_count >= MAX_LOGIN_FAIL:
        raise BusinessError(
            ErrorCode.ACCOUNT_LOCKED, "账号已锁定，请30分钟后再试"
        )

    # 重新查询含密码哈希的完整记录（仅用于密码校验）
    user_full = await user_repo.find_by_account_with_password(account)

    # 密码校验
    if not user_full or not verify_password(data.password, user_full.get("password_hash", "")):
        cur_count = await incr_login_fail(user_id)
        logger.warning(
            "登录失败: account=%s, user_id=%s, fail_count=%s", account, user_id, cur_count
        )
        raise BusinessError(
            ErrorCode.ACCOUNT_OR_PASSWORD_ERROR, "账号或密码错误"
        )

    # 登录成功：清空失败计数 + 更新最后登录时间
    await clear_login_fail(user_id)
    await user_repo.update_last_login(user_id)

    # 签发 JWT
    token = create_token(
        user_id, user_safe["username"], user_safe["role"], data.remember_me
    )
    expires_in = get_token_ttl_seconds()
    logger.info(
        "用户登录成功: user_id=%s, username=%s", user_id, user_safe["username"]
    )
    return {
        "token": token,
        "expires_in": expires_in,
        "user": {
            "user_id": user_id,
            "username": user_safe["username"],
            "role": user_safe["role"],
        },
    }


async def logout(token: str) -> None:
    """退出登录：将 token 加入黑名单（TTL 取剩余有效期）"""
    payload = decode_token(token)
    if payload and "exp" in payload:
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        remaining = int((exp - datetime.now(timezone.utc)).total_seconds())
        ttl = max(remaining, 1)
    else:
        # token 无法解析时，用默认有效期作为兜底
        ttl = get_token_ttl_seconds()
    await blacklist_token(token, ttl)
    logger.info("用户退出登录，token 已加入黑名单")


async def get_me(user_id: int) -> dict:
    """获取当前用户信息（不含密码）"""
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    return _to_user_response(user)


async def update_profile(user_id: int, data: UpdateProfileRequest) -> dict:
    """修改个人资料：校验唯一性 -> 更新"""
    # 用户名唯一性校验（排除当前用户）
    if data.username is not None:
        existing = await user_repo.find_by_username(data.username)
        if existing and existing["user_id"] != user_id:
            raise BusinessError(ErrorCode.ACCOUNT_EXISTS, "用户名已存在")
    # 手机号唯一性校验（排除当前用户）
    if data.phone is not None:
        existing = await user_repo.find_by_phone(data.phone)
        if existing and existing["user_id"] != user_id:
            raise BusinessError(ErrorCode.ACCOUNT_EXISTS, "手机号已存在")

    await user_repo.update_profile(user_id, data.username, data.phone, data.email)
    user = await user_repo.find_by_id(user_id)
    if not user:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    logger.info("用户修改资料: user_id=%s", user_id)
    return _to_user_response(user)


async def change_password(user_id: int, old_password: str, new_password: str) -> None:
    """修改密码：验证旧密码 -> 哈希新密码 -> 更新"""
    user = await user_repo.find_by_id_with_password(user_id)
    if not user:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    if not verify_password(old_password, user.get("password_hash", "")):
        raise BusinessError(ErrorCode.PARAM_ERROR, "旧密码错误")
    new_hash = hash_password(new_password)
    await user_repo.update_password(user_id, new_hash)
    logger.info("用户修改密码: user_id=%s", user_id)


async def list_users(
    keyword: Optional[str],
    status: Optional[int],
    role: Optional[str] = None,
    page_params: PageParams = PageParams(page=1, page_size=20),
) -> dict:
    """分页查询用户列表（支持按角色筛选）"""
    items = await user_repo.list_users(
        keyword, status, page_params.offset, page_params.limit, role=role
    )
    total = await user_repo.count_users(keyword, status, role=role)
    return {
        "total": total,
        "page": page_params.page,
        "page_size": page_params.page_size,
        "items": [_to_user_list_item(item) for item in items],
    }


async def update_status(
    target_id: int, status: int, current_user_id: int
) -> None:
    """管理员修改用户状态（不能操作自己）"""
    if target_id == current_user_id:
        raise BusinessError(ErrorCode.PARAM_ERROR, "不能修改自己的状态")
    target = await user_repo.find_by_id(target_id)
    if not target:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    await user_repo.update_status(target_id, status)
    logger.info(
        "修改用户状态: target_id=%s, status=%s, operator=%s",
        target_id, status, current_user_id,
    )


async def delete_user(target_id: int, current_user_id: int) -> None:
    """管理员删除用户（软删除，不能删除自己）"""
    if target_id == current_user_id:
        raise BusinessError(ErrorCode.PARAM_ERROR, "不能删除自己")
    target = await user_repo.find_by_id(target_id)
    if not target:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    await user_repo.soft_delete_user(target_id)
    logger.info(
        "删除用户(软删除): target_id=%s, operator=%s",
        target_id, current_user_id,
    )


async def reset_password(admin_id: int, target_user_id: int, new_password: str) -> None:
    """管理员重置任意用户密码"""
    if admin_id == target_user_id:
        raise BusinessError(ErrorCode.PARAM_ERROR, "不能重置自己的密码，请使用修改密码功能")
    target = await user_repo.find_by_id(target_user_id)
    if not target:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    pwd_hash = hash_password(new_password)
    await user_repo.update_password(target_user_id, pwd_hash)
    logger.info(
        "管理员重置密码: target_user_id=%s, operator=%s",
        target_user_id, admin_id,
    )


async def self_reset_password(username: str, phone: str, new_password: str) -> None:
    """自助重置密码：校验用户名和手机号匹配 -> 限流 -> 重置"""
    # 先通过用户名查找用户
    user = await user_repo.find_by_username(username)
    if not user:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户名或手机号不匹配")
    # 校验手机号是否匹配
    if user["phone"] != phone:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户名或手机号不匹配")
    # 校验用户状态
    if user["status"] == 0:
        raise BusinessError(ErrorCode.ACCOUNT_DISABLED, "账号已禁用")
    # 速率限制：按 user_id 限制，每小时最多 SELF_RESET_RATE_LIMIT 次
    rate_key = f"self_reset:{user['user_id']}"
    cur_count = await get_count(rate_key)
    if cur_count >= SELF_RESET_RATE_LIMIT:
        raise BusinessError(
            ErrorCode.RATE_LIMITED, "操作过于频繁，请稍后再试"
        )
    await incr_with_ttl(rate_key, SELF_RESET_RATE_WINDOW)
    # 重置密码
    pwd_hash = hash_password(new_password)
    await user_repo.update_password(user["user_id"], pwd_hash)
    logger.info(
        "自助重置密码: user_id=%s, username=%s",
        user["user_id"], username,
    )


async def create_agent(data: CreateAgentRequest) -> dict:
    """创建客服账号：强制 role=agent，其他同注册"""
    # 用户名唯一性校验
    if await user_repo.find_by_username(data.username):
        raise BusinessError(ErrorCode.ACCOUNT_EXISTS, "用户名已存在")
    # 手机号唯一性校验
    if await user_repo.find_by_phone(data.phone):
        raise BusinessError(ErrorCode.ACCOUNT_EXISTS, "手机号已存在")

    pwd_hash = hash_password(data.password)
    user_id = await user_repo.insert_user(
        data.username, data.phone, data.email, pwd_hash, role="agent"
    )
    logger.info("客服账号创建成功: user_id=%s, username=%s", user_id, data.username)
    return {"user_id": user_id, "username": data.username}


async def list_agents(
    keyword: Optional[str],
    status: Optional[int],
    page_params: PageParams,
) -> dict:
    """分页查询客服列表（role=agent）"""
    items = await user_repo.list_users(
        keyword, status, page_params.offset, page_params.limit, role="agent"
    )
    total = await user_repo.count_users(keyword, status, role="agent")
    return {
        "total": total,
        "page": page_params.page,
        "page_size": page_params.page_size,
        "items": [_to_user_list_item(item) for item in items],
    }


async def update_role(admin_id: int, target_id: int, new_role: str) -> None:
    """管理员修改用户角色"""
    if target_id == admin_id:
        raise BusinessError(ErrorCode.PARAM_ERROR, "不能修改自己的角色")
    target = await user_repo.find_by_id(target_id)
    if not target:
        raise BusinessError(ErrorCode.NOT_FOUND, "用户不存在")
    await user_repo.update_role(target_id, new_role)
    logger.info(
        "修改用户角色: target_id=%s, new_role=%s, operator=%s",
        target_id, new_role, admin_id,
    )
