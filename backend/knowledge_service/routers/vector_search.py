"""向量检索接口 - 供 ai_service 远程调用

所有 ChromaDB 操作通过子进程隔离执行，避免 SQLite/WAL 文件锁 hang 死主进程。
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

    ChromaDB 操作在子进程中执行，主进程不直接操作 ChromaDB。
    """
    kb_id = request.get("kb_id")
    query_embedding = request.get("query_embedding")
    top_k = request.get("top_k", settings.TOP_K)

    if not kb_id or not query_embedding:
        return success_response([], "参数缺失")

    # 子进程执行 ChromaDB 查询（即使子进程 hang，主进程不受影响）
    items = search(kb_id, query_embedding, top_k)
    return success_response(items)


@router.post("/count")
async def count_vectors(request: dict):
    """返回指定知识库的向量数量（判断知识库是否为空）

    ChromaDB 操作在子进程中执行。
    """
    kb_id = request.get("kb_id")
    if not kb_id:
        return success_response({"count": 0})

    c = count(kb_id)
    return success_response({"count": c})
