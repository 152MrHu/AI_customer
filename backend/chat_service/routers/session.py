"""对话服务路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from common.response import success_response
from common.dependencies import get_current_user
from common.pagination import get_page_params, PageParams

from chat_service.schemas.session import (
    CreateSessionRequest,
    SendMessageRequest,
)
from chat_service.services import session_service, message_service

router = APIRouter(prefix="/api/chat", tags=["对话服务"])


@router.post("/sessions", summary="创建会话")
async def create_session(
    data: CreateSessionRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """创建会话（需 Token）"""
    result = await session_service.create_session(user["user_id"], data)
    return success_response(result)


@router.post("/sessions/{session_id}/messages", summary="发送消息(SSE 流式)")
async def send_message(
    session_id: int,
    request: Request,
    body: SendMessageRequest,
    user: dict = Depends(get_current_user),
):
    """
    发送消息，返回 SSE 流式响应。
    帧类型：token / sources / done / error
    """
    user_id = user["user_id"]

    async def generate():
        async for frame in message_service.send_message(
            session_id, user_id, body.content
        ):
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


@router.get("/sessions", summary="会话列表")
async def list_sessions(
    request: Request,
    keyword: Optional[str] = None,
    user: dict = Depends(get_current_user),
    page_params: PageParams = Depends(get_page_params),
):
    """会话列表（需 Token），支持 keyword 搜索"""
    result = await session_service.list_sessions(
        user["user_id"], keyword, page_params
    )
    return success_response(result)


@router.get("/sessions/{session_id}", summary="会话详情")
async def get_session(
    session_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """会话详情（需 Token）"""
    result = await session_service.get_session_detail(session_id, user["user_id"])
    return success_response(result)


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """删除会话（软删除，需 Token）"""
    await session_service.delete_session(session_id, user["user_id"])
    return success_response(None, "删除成功")
