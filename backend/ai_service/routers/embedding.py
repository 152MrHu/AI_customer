"""文本向量化路由"""
from fastapi import APIRouter, Depends

from common.config import settings
from common.logging_config import get_logger
from common.response import success_response
from ..schemas.embedding import EmbeddingRequest
from ..dependencies import get_adapter

router = APIRouter(prefix="/api/ai", tags=["文本向量化"])
logger = get_logger()


@router.post("/embedding")
async def embedding(
    request: EmbeddingRequest,
    adapter=Depends(get_adapter),
):
    """文本向量化接口"""
    logger.info("收到向量化请求, kb_id=%s, 文本数=%d",
                request.kb_id, len(request.texts))

    embeddings = await adapter.embed(request.texts)
    dimensions = len(embeddings[0]) if embeddings else 0

    return success_response({
        "embeddings": embeddings,
        "model": settings.EMBEDDING_MODEL,
        "dimensions": dimensions,
    })
