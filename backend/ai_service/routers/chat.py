"""聊天路由 - RAG 流式问答"""
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from common.logging_config import get_logger
from ..schemas.chat import RagChatRequest
from ..services.rag_service import rag_chat
from ..dependencies import get_adapter, get_chroma_client

router = APIRouter(prefix="/api/ai", tags=["AI 对话"])
logger = get_logger()


@router.post("/chat")
async def chat(
    request: RagChatRequest,
    adapter=Depends(get_adapter),
    chroma_client=Depends(get_chroma_client),
):
    """
    RAG 流式问答接口
    返回 SSE 流：逐 token 输出，最后附 sources 与 done 帧
    """
    logger.info("收到 RAG 问答请求, kb_id=%s, query=%s",
                request.knowledge_base_id, request.query[:50])

    async def generate():
        async for frame in rag_chat(request, adapter, chroma_client):
            yield frame

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
