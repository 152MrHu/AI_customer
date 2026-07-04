"""用户服务路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Request

from common.response import success_response, ErrorCode
from common.exceptions import BusinessError
from common.dependencies import get_current_user, require_admin
from common.pagination import get_page_params, PageParams

from user_service.schemas.user import (
    RegisterRequest,
    LoginRequest,
    UpdateStatusRequest,
)
from user_service.services import user_service

router = APIRouter(prefix="/api/user", tags=["用户服务"])


@router.post("/register", summary="用户注册")
async def register(data: RegisterRequest):
    """用户注册（公开接口）"""
    result = await user_service.register(data)
    return success_response(result)


@router.post("/login", summary="用户登录")
async def login(data: LoginRequest):
    """用户登录（公开接口）"""
    result = await user_service.login(data)
    return success_response(result)


@router.post("/logout", summary="退出登录")
async def logout(request: Request):
    """退出登录（需 Token），将 token 加入黑名单"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise BusinessError(ErrorCode.UNAUTHORIZED, "缺少有效的认证信息")
    token = auth[len("Bearer "):]
    await user_service.logout(token)
    return success_response(None, "退出登录成功")


@router.get("/me", summary="获取个人信息")
async def me(user: dict = Depends(get_current_user)):
    """获取当前登录用户信息（需 Token）"""
    result = await user_service.get_me(user["user_id"])
    return success_response(result)


@router.get("/list", summary="用户列表")
async def list_users(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    admin: dict = Depends(require_admin),
    page_params: PageParams = Depends(get_page_params),
):
    """用户列表（管理员）"""
    result = await user_service.list_users(keyword, status, page_params)
    return success_response(result)


@router.put("/{user_id}/status", summary="修改用户状态")
async def update_status(
    user_id: int,
    data: UpdateStatusRequest,
    admin: dict = Depends(require_admin),
):
    """修改用户状态（管理员，不能操作自己）"""
    await user_service.update_status(user_id, data.status, admin["user_id"])
    return success_response(None, "状态修改成功")


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_admin),
):
    """删除用户（管理员软删除，不能删除自己）"""
    await user_service.delete_user(user_id, admin["user_id"])
    return success_response(None, "删除成功")
