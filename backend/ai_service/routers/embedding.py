"""文本向量化路由"""
from fastapi import APIRouter, Depends

from common.config import settings
from common.logging_config import get_logger
from common.response import success_response, error_response, ErrorCode
from ..schemas.embedding import EmbeddingRequest
from ..dependencies import get_adapter

router = APIRouter(prefix="/api/ai", tags=["文本向量化"])
logger = get_logger()


@router.post("/embedding")
async def embedding(
    request: EmbeddingRequest,
    adapter=Depends(get_adapter),
):
    """文本向量化接口（自动分批，每批≤10条）"""
    logger.info("收到向量化请求, kb_id=%s, 文本数=%d",
                request.kb_id, len(request.texts))

    try:
        embeddings = await adapter.embed(request.texts)
    except Exception as e:
        logger.error("向量化失败: kb_id=%s, 文本数=%d, error=%s",
                     request.kb_id, len(request.texts), e)
        return error_response(ErrorCode.AI_UNAVAILABLE, f"向量化失败: {str(e)}")

    if not embeddings:
        return error_response(ErrorCode.AI_UNAVAILABLE, "向量化返回空结果")

    dimensions = len(embeddings[0]) if embeddings else 0

    return success_response({
        "embeddings": embeddings,
        "model": settings.EMBEDDING_MODEL,
        "dimensions": dimensions,
    })
