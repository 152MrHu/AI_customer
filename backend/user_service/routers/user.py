"""用户服务路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Request

from common.response import success_response, ErrorCode
from common.exceptions import BusinessError
from common.dependencies import get_current_user, require_admin, require_agent
from common.pagination import get_page_params, PageParams

from user_service.schemas.user import (
    RegisterRequest,
    LoginRequest,
    UpdateStatusRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    ResetPasswordRequest,
    SelfResetRequest,
    CreateAgentRequest,
    UpdateRoleRequest,
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


@router.put("/profile", summary="修改个人资料")
async def update_profile(
    data: UpdateProfileRequest,
    user: dict = Depends(get_current_user),
):
    """修改个人资料（需 Token）"""
    result = await user_service.update_profile(user["user_id"], data)
    return success_response(result)


@router.put("/password", summary="修改密码")
async def change_password(
    data: ChangePasswordRequest,
    user: dict = Depends(get_current_user),
):
    """修改密码（需 Token）"""
    await user_service.change_password(user["user_id"], data.old_password, data.new_password)
    return success_response(None, "密码修改成功")


@router.get("/list", summary="用户列表")
async def list_users(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    role: Optional[str] = None,
    admin: dict = Depends(require_admin),
    page_params: PageParams = Depends(get_page_params),
):
    """用户列表（管理员）"""
    result = await user_service.list_users(keyword, status, role, page_params)
    return success_response(result)


@router.post("/agents", summary="创建客服账号")
async def create_agent(
    data: CreateAgentRequest,
    admin: dict = Depends(require_admin),
):
    """创建客服账号（管理员）"""
    result = await user_service.create_agent(data)
    return success_response(result)


@router.get("/agents", summary="客服列表")
async def list_agents(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    user: dict = Depends(require_agent),
    page_params: PageParams = Depends(get_page_params),
):
    """客服列表（管理员/客服）"""
    result = await user_service.list_agents(keyword, status, page_params)
    return success_response(result)


@router.put("/users/{user_id}/role", summary="修改用户角色")
async def update_user_role(
    user_id: int,
    data: UpdateRoleRequest,
    admin: dict = Depends(require_admin),
):
    """修改用户角色（管理员）"""
    await user_service.update_role(admin["user_id"], user_id, data.role)
    return success_response(None, "角色修改成功")


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


@router.post("/reset-password", summary="管理员重置密码")
async def reset_password(
    data: ResetPasswordRequest,
    admin: dict = Depends(require_admin),
):
    """管理员重置任意用户密码（管理员）"""
    await user_service.reset_password(admin["user_id"], data.user_id, data.new_password)
    return success_response(None, "密码重置成功")


@router.post("/forgot-password", summary="自助重置密码")
async def forgot_password(data: SelfResetRequest):
    """自助重置密码（公开接口，验证用户名和手机号）"""
    await user_service.self_reset_password(data.username, data.phone, data.new_password)
    return success_response(None, "密码重置成功")
