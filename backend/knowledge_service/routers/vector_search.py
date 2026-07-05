"""向量检索接口 - 供 ai_service 远程调用

使用 SQLite + numpy 实现向量存储和检索，无 Rust/C++ 依赖，不会 segfault。
"""
from fastapi import APIRouter

from common.config import settings
from common.response import success_response
from ..vector_store import search, count

router = APIRouter(prefix="/api/knowledge", tags=["向量检索"])


@router.post("/search")
async def vector_search(request: dict):
    """
    向量检索接口（内部服务调用，无需认证）。

    请求体：
    {
        "kb_id": 1,
        "query_embedding": [0.1, 0.2, ...],
        "top_k": 5
    }
    """
    kb_id = request.get("kb_id")
    query_embedding = request.get("query_embedding")
    top_k = request.get("top_k", settings.TOP_K)

    if not kb_id or not query_embedding:
        return success_response([], "参数缺失")

    # SQLite + numpy 向量检索（不会 segfault）
    items = search(kb_id, query_embedding, top_k)
    return success_response(items)


@router.post("/count")
async def count_vectors(request: dict):
    """返回指定知识库的向量数量（判断知识库是否为空）"""
    kb_id = request.get("kb_id")
    if not kb_id:
        return success_response({"count": 0})

    c = count(kb_id)
    return success_response({"count": c})
