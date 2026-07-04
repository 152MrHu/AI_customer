"""统一响应格式封装"""
from typing import Any, Optional
from fastapi.responses import JSONResponse


# ========== 错误码常量 ==========
class ErrorCode:
    SUCCESS = 200
    PARAM_ERROR = 1001
    NOT_FOUND = 1002
    ACCOUNT_EXISTS = 2001
    ACCOUNT_OR_PASSWORD_ERROR = 2002
    ACCOUNT_DISABLED = 2003
    ACCOUNT_LOCKED = 2004
    SESSION_NOT_FOUND = 3001
    MESSAGE_EMPTY = 3002
    DOC_FORMAT_UNSUPPORTED = 4001
    FILE_TOO_LARGE = 4002
    DOC_INGEST_FAILED = 4003
    KB_NAME_EXISTS = 4004
    AI_TIMEOUT = 5001
    AI_UNAVAILABLE = 5002
    KB_EMPTY = 5003
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    RATE_LIMITED = 429
    SERVER_ERROR = 500


ERROR_MESSAGES = {
    200: "success",
    1001: "参数错误",
    1002: "资源不存在",
    2001: "账号已存在",
    2002: "账号或密码错误",
    2003: "账号已禁用",
    2004: "账号已锁定",
    3001: "会话不存在",
    3002: "消息内容为空",
    4001: "文档格式不支持",
    4002: "文件超过大小限制",
    4003: "文档入库失败",
    4004: "知识库名称已存在",
    5001: "AI服务超时",
    5002: "AI服务不可用",
    5003: "知识库为空",
    401: "未授权",
    403: "禁止访问",
    429: "请求过多",
    500: "服务器错误",
}


def success_response(data: Any = None, message: str = "success") -> dict:
    return {"code": ErrorCode.SUCCESS, "message": message, "data": data}


def error_response(code: int, message: str = None, data: Any = None) -> dict:
    if message is None:
        message = ERROR_MESSAGES.get(code, "未知错误")
    return {"code": code, "message": message, "data": data}


def paginated_response(items: list, total: int, page: int, page_size: int) -> dict:
    return {
        "code": ErrorCode.SUCCESS,
        "message": "success",
        "data": {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        },
    }
