"""健康检查路由"""
from fastapi import APIRouter

from common.config import settings
from common.response import success_response

router = APIRouter(prefix="/api/ai", tags=["健康检查"])


@router.get("/health")
async def health():
    """AI 服务健康检查"""
    return success_response({
        "status": "healthy",
        "model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    })
