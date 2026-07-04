"""网关反向代理 - 核心转发逻辑"""
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, Response

from common.http_client import get_client
from common.response import error_response
from common.logging_config import get_logger

from gateway.routes import match_target, is_sse_path

router = APIRouter()
logger = get_logger()

# hop-by-hop 请求头（不应被代理转发）
HOP_BY_HOP_REQ = {
    "host", "content-length", "transfer-encoding",
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "upgrade",
}

# hop-by-hop 响应头
HOP_BY_HOP_RESP = {
    "content-encoding", "transfer-encoding", "content-length",
    "connection", "keep-alive", "proxy-authenticate",
    "proxy-authorization", "te", "trailers", "upgrade",
}


@router.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
)
async def proxy(request: Request, path: str):
    """通配反向代理：根据路径前缀转发到对应下游服务"""
    full_path = f"/{path}"
    target_base = match_target(full_path)
    if not target_base:
        return error_response(404, f"路径不存在: {full_path}")

    target = f"{target_base}{full_path}"

    # 透传请求头（移除 hop-by-hop，保留 X-User-Id / X-User-Role 等）
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in HOP_BY_HOP_REQ
    }

    # 获取请求体
    body = await request.body()

    # query 参数透传
    query_params = list(request.query_params.multi_items())

    client = get_client()

    # SSE 流式转发
    if is_sse_path(full_path, request.method):
        logger.info("SSE 流式转发: %s %s -> %s", request.method, full_path, target)

        async def stream_response():
            try:
                async with client.stream(
                    "POST", target,
                    content=body,
                    headers=headers,
                    params=query_params,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
            except httpx.RequestError as e:
                logger.error("SSE 转发网络异常: %s, err=%s", target, e)
                # 生成一个 SSE error 帧
                import json
                payload = json.dumps(
                    {"type": "error", "code": 5002, "message": "下游服务不可用"},
                    ensure_ascii=False,
                )
                yield f"data: {payload}\n\n".encode("utf-8")

        return StreamingResponse(
            stream_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # 普通 HTTP 转发
    try:
        resp = await client.request(
            request.method, target,
            content=body,
            headers=headers,
            params=query_params,
        )
    except httpx.RequestError as e:
        logger.error("转发请求异常: %s %s, err=%s", request.method, target, e)
        return error_response(5002, f"下游服务不可用: {e}")

    # 透传响应头（移除 hop-by-hop）
    resp_headers = {
        k: v for k, v in resp.headers.items()
        if k.lower() not in HOP_BY_HOP_RESP
    }

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
        media_type=resp.headers.get("content-type"),
    )
