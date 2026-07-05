"""向量检索接口 - 供 ai_service 远程调用，避免多进程 ChromaDB 锁冲突"""
from typing import Optional

from fastapi import APIRouter

from common.config import settings
from common.response import success_response
from ..vector_store import get_client

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

    返回检索结果列表，每项含 doc_name / score / snippet / document。
    ChromaDB 余弦距离 (0~2) → score = 1 - distance
    """
    kb_id = request.get("kb_id")
    query_embedding = request.get("query_embedding")
    top_k = request.get("top_k", settings.TOP_K)

    if not kb_id or not query_embedding:
        return success_response([], "参数缺失")

    try:
        client = get_client()
        collection = client.get_collection(name=f"kb_{kb_id}")

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        if not results or not results.get("ids") or not results["ids"][0]:
            return success_response([])

        ids = results["ids"][0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        items = []
        for i in range(len(ids)):
            distance = distances[i] if i < len(distances) else 1.0
            score = round(1.0 - distance, 4)
            meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            document = documents[i] if i < len(documents) else ""
            doc_name = (
                meta.get("file_name") or meta.get("doc_name")
                or meta.get("source") or "未知文档"
            )
            items.append({
                "doc_name": doc_name,
                "score": score,
                "snippet": document[:200] if document else "",
                "document": document,
            })

        return success_response(items)

    except Exception as e:
        # collection 不存在等异常返回空结果
        return success_response([])


@router.post("/count")
async def count_vectors(request: dict):
    """返回指定知识库的向量数量（判断知识库是否为空）"""
    kb_id = request.get("kb_id")
    if not kb_id:
        return success_response({"count": 0})

    try:
        client = get_client()
        collection = client.get_collection(name=f"kb_{kb_id}")
        count = collection.count()
        return success_response({"count": count})
    except Exception as e:
        return success_response({"count": 0})
