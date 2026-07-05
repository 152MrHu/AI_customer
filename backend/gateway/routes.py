"""网关路由转发规则"""
from common.config import settings

# 公开接口（无需鉴权）
PUBLIC_PATHS = {
    "/api/user/register",
    "/api/user/login",
}

# 路由表：路径前缀 -> 目标服务 URL
ROUTE_TABLE = [
    ("/api/user", settings.USER_SERVICE_URL),
    ("/api/chat", settings.CHAT_SERVICE_URL),
    ("/api/knowledge", settings.KNOWLEDGE_SERVICE_URL),
    ("/api/ai", settings.AI_SERVICE_URL),
]


def match_target(path: str) -> str | None:
    """根据请求路径匹配目标服务 URL，未匹配返回 None"""
    for prefix, url in ROUTE_TABLE:
        if path.startswith(prefix):
            return url
    return None


def is_public(path: str) -> bool:
    """是否为公开接口（无需鉴权）"""
    return path in PUBLIC_PATHS


def is_admin_path(path: str) -> bool:
    """知识库管理接口需要管理员权限"""
    return path.startswith("/api/knowledge")


def is_upload_path(path: str, method: str) -> bool:
    """是否为文件上传接口（需要更长的转发超时）"""
    return (
        path.startswith("/api/knowledge/bases/")
        and path.endswith("/documents")
        and method == "POST"
    )


def is_rate_limited(path: str, method: str) -> bool:
    """AI 问答接口需要限流：POST /api/chat/sessions/{id}/messages"""
    return (
        path.startswith("/api/chat/sessions/")
        and path.endswith("/messages")
        and method == "POST"
    )


def is_sse_path(path: str, method: str) -> bool:
    """是否为 SSE 流式接口（需要流式转发）"""
    return (
        path.startswith("/api/chat/sessions/")
        and path.endswith("/messages")
        and method == "POST"
    )
