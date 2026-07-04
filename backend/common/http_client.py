"""HTTP 客户端 - httpx 异步，用于服务间调用"""
import httpx
from typing import AsyncGenerator, Optional
from common.config import settings

_client: Optional[httpx.AsyncClient] = None


async def create_client():
    global _client
    _client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=5.0))
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
