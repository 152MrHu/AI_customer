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
    """知识库管理接口需要管理员权限（列表查询除外，供用户选择知识库）"""
    # GET 知识库列表接口对已认证用户开放
    if path == "/api/knowledge/bases/available":
        return False
    return path.startswith("/api/knowledge")


def is_upload_path(path: str, method: str) -> bool:
    """是否为文件上传接口（需要更长的转发超时）"""
    return (
        path.startswith("/api/knowledge/bases/")
        and path.endswith("/documents")
        and method == "POST"
    )


def is_rate_limited(path: str, method: str) -> bool:
    """以下接口需要限流：
    - AI 问答：POST /api/chat/sessions/{id}/messages
    - 文件上传：POST /api/chat/upload
    - 登录：POST /api/user/login
    - 注册：POST /api/user/register
    - 知识库文档上传：POST /api/knowledge/bases/{id}/documents
    """
    if method != "POST":
        return False
    # AI 问答接口
    if path.startswith("/api/chat/sessions/") and path.endswith("/messages"):
        return True
    # 聊天文件上传
    if path == "/api/chat/upload":
        return True
    # 登录 + 注册
    if path in ("/api/user/login", "/api/user/register"):
        return True
    # 文档上传
    if path.startswith("/api/knowledge/bases/") and path.endswith("/documents"):
        return True
    return False


def is_sse_path(path: str, method: str) -> bool:
    """是否为 SSE 流式接口（需要流式转发）"""
    if method != "POST":
        return False
    if path.startswith("/api/chat/sessions/") and path.endswith("/messages"):
        return True
    if path.startswith("/api/chat/sessions/") and path.endswith("/agent-message"):
        return True
    return False
