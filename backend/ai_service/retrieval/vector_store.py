"""ChromaDB 向量存储只读检索封装"""
from typing import Optional

from common.logging_config import get_logger

logger = get_logger()


class VectorStore:
    """ChromaDB 检索封装（只读）"""

    def __init__(self, chroma_client):
        self.client = chroma_client

    def get_collection(self, kb_id: int):
        """获取或创建 collection（名称 kb_{kb_id}）"""
        collection_name = f"kb_{kb_id}"
        collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        return collection

    def query(self, kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[dict]:
        """
        向量检索：
        调用 collection.query，返回 [{"doc_name", "score", "snippet", "document"}]
        ChromaDB distances 为余弦距离 (0~2)，score = 1 - distance
        """
        collection = self.get_collection(kb_id)
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error("ChromaDB query 失败, kb_id=%s: %s", kb_id, e)
            return []

        if not results or not results.get("ids") or not results["ids"][0]:
            return []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        items: list[dict] = []
        for i in range(len(ids)):
            distance = distances[i] if i < len(distances) else 1.0
            # 余弦距离 0~2，转换为相似度得分
            score = 1.0 - distance
            meta = metadatas[i] if i < len(metadatas) and metadatas[i] else {}
            document = documents[i] if i < len(documents) else ""
            doc_name = (
                meta.get("file_name")
                or meta.get("doc_name")
                or meta.get("source")
                or "未知文档"
            )
            items.append({
                "doc_name": doc_name,
                "score": round(score, 4),
                "snippet": document[:200] if document else "",
                "document": document,
            })
        return items

    def count_collection(self, kb_id: int) -> int:
        """返回 collection 中向量数量（判断知识库是否为空）"""
        try:
            collection = self.get_collection(kb_id)
            return collection.count()
        except Exception as e:
            logger.error("ChromaDB count 失败, kb_id=%s: %s", kb_id, e)
            return 0
