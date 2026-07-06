"""SSE (Server-Sent Events) 帧序列化辅助工具 - 共享模块"""
import json
from typing import List, Optional


def format_sse(payload: dict) -> str:
    """格式化 SSE 数据帧: data: {...}\n\n"""
    try:
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    except (TypeError, ValueError) as e:
        # 兜底：序列化失败时返回错误帧
        return f"data: {json.dumps({'type': 'error', 'code': 5000, 'message': '序列化失败'}, ensure_ascii=False)}\n\n"


def token_frame(content: str) -> str:
    """生成 token 文本片段帧"""
    return format_sse({"type": "token", "content": content})


def sources_frame(sources: List[dict]) -> str:
    """生成检索来源帧"""
    return format_sse({"type": "sources", "sources": sources})


def done_frame(message_id: Optional[int] = None) -> str:
    """生成结束帧"""
    payload = {"type": "done"}
    if message_id is not None:
        payload["message_id"] = message_id
    return format_sse(payload)


def error_frame(code: int, message: str) -> str:
    """生成错误帧"""
    return format_sse({"type": "error", "code": code, "message": message})
