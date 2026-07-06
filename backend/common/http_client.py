"""HTTP 客户端 - httpx 异步，用于服务间调用"""
import contextvars
from typing import AsyncGenerator, Optional

import httpx
from common.config import settings

_client: Optional[httpx.AsyncClient] = None

# 请求 ID 上下文变量，用于在服务间调用时透传 X-Request-Id
_request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)


def set_request_id(request_id: str) -> None:
    """设置当前请求的 X-Request-Id (contextvars)"""
    _request_id_var.set(request_id)


def get_request_id() -> Optional[str]:
    """获取当前请求的 X-Request-Id (contextvars)"""
    return _request_id_var.get()


async def create_client():
    global _client
    # 禁用 keep-alive，每次请求新建连接，彻底避免下游服务重启后复用死连接的问题
    _client = httpx.AsyncClient(
        timeout=httpx.Timeout(30.0, connect=5.0),
        limits=httpx.Limits(max_keepalive_connections=0),
    )
    return _client


async def close_client():
    global _client
    if _client:
        await _client.aclose()
        _client = None


def get_client() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("httpx 客户端未初始化")
    return _client


def get_client_with_tracing() -> httpx.AsyncClient:
    """返回一个 httpx 客户端，自动转发当前上下文的 X-Request-Id 请求头"""
    client = get_client()
    request_id = get_request_id()
    if request_id:
        client.headers.update({"X-Request-Id": request_id})
    return client


async def post_json(url: str, json: dict, headers: dict = None) -> httpx.Response:
    """POST JSON 请求"""
    client = get_client()
    resp = await client.post(url, json=json, headers=headers or {})
    return resp


async def get_json(url: str, params: dict = None, headers: dict = None) -> httpx.Response:
    """GET 请求"""
    client = get_client()
    resp = await client.get(url, params=params, headers=headers or {})
    return resp


async def stream_post(url: str, json: dict, headers: dict = None) -> AsyncGenerator[str, None]:
    """流式 POST 请求，逐行 yield 响应文本（用于 SSE 透传）"""
    client = get_client()
    async with client.stream("POST", url, json=json, headers=headers or {}) as resp:
        async for line in resp.aiter_lines():
            yield line
