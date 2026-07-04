"""ChromaDB 向量存储封装（写入/删除）

knowledge-service 负责写入，ai-service 负责读取，共用同一持久化目录。
"""
import chromadb

from common.config import settings
from common.logging_config import get_logger

logger = get_logger()

_client = None


def get_client():
    """获取 ChromaDB 持久化客户端（单例）"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_path)
    return _client


def create_collection(kb_id: int):
    """创建知识库时创建 collection"""
    client = get_client()
    client.get_or_create_collection(
        name=f"kb_{kb_id}",
        metadata={"hnsw:space": "cosine"},
    )
    logger.info("ChromaDB collection 已创建: kb_%s", kb_id)


def add_chunks(
    kb_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: int,
    file_name: str,
):
    """写入向量数据"""
    client = get_client()
    collection = client.get_collection(name=f"kb_{kb_id}")
    ids = [f"{document_id}_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "document_id": document_id,
            "file_name": file_name,
            "chunk_index": i,
            "source": file_name,
        }
        for i in range(len(chunks))
    ]
    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    logger.info(
        "ChromaDB 写入完成: kb_%s, document_id=%s, chunks=%d",
        kb_id, document_id, len(chunks),
    )


def delete_by_document(kb_id: int, document_id: int):
    """按文档 ID 删除该文档的所有向量"""
    client = get_client()
    collection = client.get_collection(name=f"kb_{kb_id}")
    collection.delete(where={"document_id": document_id})
    logger.info(
        "ChromaDB 删除完成: kb_%s, document_id=%s",
        kb_id, document_id,
    )
