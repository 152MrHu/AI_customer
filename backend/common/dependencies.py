"""FastAPI 公共依赖"""
from fastapi import Request, Header
from typing import Optional
from common.exceptions import BusinessError


def get_current_user(
    request: Request,
) -> dict:
    """从 Gateway 透传的 X-User-Id / X-User-Role 请求头获取用户信息"""
    user_id = request.headers.get("X-User-Id")
    user_role = request.headers.get("X-User-Role")
    if not user_id:
        raise BusinessError(401, "未授权")
    return {"user_id": int(user_id), "role": user_role or "user"}


def require_admin(request: Request) -> dict:
    """要求管理员权限"""
    user = get_current_user(request)
    if user["role"] != "admin":
        raise BusinessError(403, "禁止访问：需要管理员权限")
    return user
