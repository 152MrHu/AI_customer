"""对话服务路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from common.response import success_response, paginated_response, ErrorCode
from common.dependencies import get_current_user, require_agent
from common.pagination import get_page_params, PageParams
from common.exceptions import BusinessError

from chat_service.schemas.session import (
    CreateSessionRequest,
    SendMessageRequest,
    AgentMessageRequest,
)
from chat_service.schemas.feedback import FeedbackRequest
from chat_service.schemas.handoff import CreateHandoffRequest, ResolveHandoffRequest
from chat_service.services import session_service, message_service
from chat_service.repositories import message_repo, feedback_repo, handoff_repo, session_repo

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
    """会话详情（需 Token）。会话拥有者可访问；客服已认领该会话转接工单也可访问"""
    # 先尝试常规用户归属校验
    try:
        result = await session_service.get_session_detail(session_id, user["user_id"])
        return success_response(result)
    except BusinessError as e:
        if e.code == ErrorCode.SESSION_NOT_FOUND and user.get("role") in ("admin", "agent"):
            # 客服/管理员检查是否已认领该会话的工单
            ticket = await handoff_repo.find_claimed_by_session_and_user(session_id, user["user_id"])
            if not ticket:
                raise
            session = await session_repo.find_by_id(session_id)
            if not session:
                raise BusinessError(ErrorCode.SESSION_NOT_FOUND, "会话不存在")
            kb_id = session.get("kb_id")
            mode = session.get("mode", "kb")
            kb_name = await session_service._get_kb_name(kb_id) if mode == "kb" and kb_id else ""
            messages = await message_repo.find_by_session(session_id)
            # 构造响应（复用 session_service 的格式）
            result = session_service._to_session_detail(session, messages, kb_name)
            return success_response(result)
        raise


@router.delete("/sessions/{session_id}", summary="删除会话")
async def delete_session(
    session_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """删除会话（软删除，需 Token）"""
    await session_service.delete_session(session_id, user["user_id"])
    return success_response(None, "删除成功")


@router.post("/messages/{message_id}/feedback", summary="提交消息反馈")
async def submit_feedback(
    message_id: int,
    body: FeedbackRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """对某条消息提交赞/踩反馈（需 Token）。同一用户重复提交会覆盖之前的反馈。"""
    message = await message_repo.find_by_id(message_id)
    if not message:
        raise BusinessError(1002, "消息不存在")

    await feedback_repo.upsert_feedback(
        message_id=message_id,
        user_id=user["user_id"],
        rating=body.rating,
        comment=body.comment,
    )
    return success_response(None, "反馈提交成功")


# ========== 人工转接工单 ==========


@router.post("/sessions/{session_id}/handoff", summary="创建转接工单")
async def create_handoff(
    session_id: int,
    body: CreateHandoffRequest,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """创建人工转接工单，需验证会话归属当前用户"""
    session = await session_repo.find_by_id_and_user(session_id, user["user_id"])
    if not session:
        raise BusinessError(1002, "会话不存在或不属于当前用户")

    ticket_id = await handoff_repo.create_ticket(session_id, user["user_id"], body.reason)
    return success_response({"ticket_id": ticket_id}, "转接工单创建成功")


@router.get("/handoff/tickets", summary="查询转接工单列表")
async def list_handoff_tickets(
    request: Request,
    status: Optional[str] = None,
    claimed_by: Optional[str] = None,
    user: dict = Depends(get_current_user),
    page_params: PageParams = Depends(get_page_params),
):
    """
    查询转接工单列表。
    - 普通用户仅查看自己的工单
    - 管理员/客服可查看全部，支持 claimed_by=me 筛选自己的工单
    """
    user_role = user["role"]

    # Parse claimed_by param
    claimed_by_id = None
    if claimed_by == "me":
        claimed_by_id = user["user_id"]
    elif claimed_by and claimed_by.isdigit():
        claimed_by_id = int(claimed_by)

    if user_role == "user":
        # Regular user: only see own tickets
        total = await handoff_repo.count_tickets(
            user_id=user["user_id"], status=status
        )
        items = await handoff_repo.list_tickets(
            user_id=user["user_id"],
            status=status,
            offset=page_params.offset,
            limit=page_params.limit,
        )
    else:
        # Agent/admin: filter by claimed_by if specified
        total = await handoff_repo.count_tickets(status=status, claimed_by=claimed_by_id)
        items = await handoff_repo.list_tickets(
            status=status,
            claimed_by=claimed_by_id,
            offset=page_params.offset,
            limit=page_params.limit,
        )
    return paginated_response(items, total, page_params.page, page_params.page_size)


@router.get("/handoff/pending-count", summary="待处理工单数量")
async def pending_handoff_count(
    request: Request,
    user: dict = Depends(require_agent),
):
    """查询待处理工单数量（用于通知角标）"""
    count = await handoff_repo.get_pending_count()
    return success_response({"count": count})


@router.put("/handoff/{ticket_id}/claim", summary="认领转接工单")
async def claim_handoff(
    ticket_id: int,
    request: Request,
    user: dict = Depends(require_agent),
):
    """客服/管理员认领转接工单"""
    affected = await handoff_repo.claim_ticket(ticket_id, user["user_id"])
    if not affected:
        raise BusinessError(1002, "工单不存在或状态不允许认领")
    return success_response(None, "认领成功")


@router.put("/handoff/{ticket_id}/resolve", summary="解决转接工单")
async def resolve_handoff(
    ticket_id: int,
    body: ResolveHandoffRequest,
    request: Request,
    user: dict = Depends(require_agent),
):
    """客服/管理员解决转接工单"""
    affected = await handoff_repo.resolve_ticket(ticket_id, body.resolution)
    if not affected:
        raise BusinessError(1002, "工单不存在或状态不允许解决")
    return success_response(None, "解决成功")


@router.post("/handoff/{ticket_id}/close", summary="关闭转接工单")
async def close_handoff(
    ticket_id: int,
    request: Request,
    user: dict = Depends(get_current_user),
):
    """用户关闭自己的转接工单（仅 resolved 状态可关闭）"""
    ticket = await handoff_repo.find_by_id(ticket_id)
    if not ticket:
        raise BusinessError(1002, "工单不存在")
    if ticket["user_id"] != user["user_id"]:
        raise BusinessError(403, "禁止操作：只能关闭自己的工单")

    affected = await handoff_repo.close_ticket(ticket_id)
    if not affected:
        raise BusinessError(1002, "工单不存在或状态不允许关闭")
    return success_response(None, "关闭成功")


@router.post("/sessions/{session_id}/agent-message", summary="客服发送消息")
async def agent_send_message(
    session_id: int,
    body: AgentMessageRequest,
    request: Request,
    user: dict = Depends(require_agent),
):
    """
    客服发送消息到已认领的会话。
    认证：需客服/管理员权限且已认领对应会话的转接工单。
    返回 SSE 流式响应。
    """
    async def generate():
        async for frame in message_service.send_agent_message(
            session_id, user["user_id"], body.content
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
