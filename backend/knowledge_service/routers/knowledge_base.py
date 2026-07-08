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
    user: dict = Depends(require_admin),
):
    """创建知识库（管理员）"""
    kb = await kb_service.create_kb(request.model_dump())
    return success_response(kb)


@router.get("/bases")
async def list_kbs(
    page_params: PageParams = Depends(get_page_params),
    user: dict = Depends(require_admin),
):
    """知识库列表（管理员）"""
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
    """获取可用知识库列表（所有已认证用户可访问，用于会话创建时选择知识库）"""
    result = await kb_service.list_available_kbs()
    return success_response(result)


@router.delete("/bases/{kb_id}")
async def delete_kb(
    kb_id: int,
    user: dict = Depends(require_admin),
):
    """删除知识库（管理员）- 同时删除所有文档和 ChromaDB 数据"""
    await kb_service.delete_kb(kb_id)
    return success_response(message="知识库已删除")
