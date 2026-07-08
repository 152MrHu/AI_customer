"""文档路由"""
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, Query

from common.config import settings
from common.dependencies import get_current_user
from common.pagination import get_page_params, PageParams
from common.response import success_response, paginated_response

from ..services import document_service
from ..services import kb_service

router = APIRouter(prefix="/api/knowledge", tags=["文档管理"])


@router.post("/bases/{kb_id}/documents")
async def upload_document(
    kb_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """上传文档（知识库 owner 或 admin 可操作）"""
    await kb_service.check_kb_ownership(kb_id, user["user_id"], user.get("role", "user"))
    doc = await document_service.upload_document(kb_id, file, settings.upload_dir_path)
    return success_response(doc)


@router.get("/bases/{kb_id}/documents")
async def list_documents(
    kb_id: int,
    keyword: Optional[str] = Query(None, description="文件名关键词"),
    status: Optional[str] = Query(None, description="文档状态"),
    page_params: PageParams = Depends(get_page_params),
    user: dict = Depends(get_current_user),
):
    """文档列表（知识库 owner 或 admin 可查看）"""
    await kb_service.check_kb_ownership(kb_id, user["user_id"], user.get("role", "user"))
    result = await document_service.list_documents(kb_id, keyword, status, page_params)
    return paginated_response(
        items=result["items"],
        total=result["total"],
        page=page_params.page,
        page_size=page_params.page_size,
    )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    user: dict = Depends(get_current_user),
):
    """删除文档（文档所属知识库的 owner 或 admin 可操作）"""
    await document_service.delete_document(
        document_id, user["user_id"], user.get("role", "user")
    )
    return success_response(message="文档已删除")