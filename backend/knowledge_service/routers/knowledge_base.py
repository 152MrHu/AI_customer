"""知识库路由"""
from fastapi import APIRouter, Depends

from common.dependencies import require_admin, get_current_user
from common.pagination import get_page_params, PageParams
from common.response import success_response, paginated_response

from ..schemas.kb import CreateKbRequest
from ..services import kb_service

router = APIRouter(prefix="/api/knowledge", tags=["知识库管理"])


@router.post("/bases")
async def create_kb(
    request: CreateKbRequest,
    user: dict = Depends(get_current_user),
):
    """创建知识库（所有已认证用户）。
    admin 创建 → owner_id=NULL（公共），普通用户/客服创建 → owner_id=user_id（私有）
    """
    role = user.get("role", "user")
    owner_id = None if role == "admin" else user["user_id"]
    kb = await kb_service.create_kb(request.model_dump(), owner_id)
    return success_response(kb)


@router.get("/bases")
async def list_kbs(
    page_params: PageParams = Depends(get_page_params),
    user: dict = Depends(require_admin),
):
    """知识库列表（管理员专用，查看全部）"""
    result = await kb_service.list_kbs(page_params)
    return paginated_response(
        items=result["items"],
        total=result["total"],
        page=page_params.page,
        page_size=page_params.page_size,
    )


@router.get("/bases/available")
async def list_available_kbs(
    user: dict = Depends(get_current_user),
):
    """获取可用知识库列表（所有已认证用户可访问，用于会话创建时选择知识库）
    admin → 全部，普通用户 → 公共 + 自己创建的
    """
    result = await kb_service.list_available_kbs(
        user_id=user["user_id"],
        role=user.get("role", "user"),
    )
    return success_response(result)


@router.delete("/bases/{kb_id}")
async def delete_kb(
    kb_id: int,
    user: dict = Depends(get_current_user),
):
    """删除知识库（owner 或 admin 可操作）"""
    await kb_service.delete_kb(kb_id, user["user_id"], user.get("role", "user"))
    return success_response(message="知识库已删除")