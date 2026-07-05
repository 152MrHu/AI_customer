"""ChromaDB 向量存储封装（写入/删除）

knowledge-service 负责写入，ai-service 负责读取（通过 HTTP 远程调用）。
ChromaDB 使用 PersistentClient，在 Windows 上需要注意 SQLite 文件锁问题。
"""
import time
import chromadb

from common.config import settings
from common.logging_config import get_logger

logger = get_logger()

_client = None
_INIT_TIMEOUT = 10  # ChromaDB 初始化超时（秒）


def get_client():
    """获取 ChromaDB 持久化客户端（单例），带超时保护"""
    global _client
    if _client is None:
        try:
            start = time.time()
            _client = chromadb.PersistentClient(path=settings.chroma_path)
            elapsed = time.time() - start
            logger.info("ChromaDB 客户端初始化完成, 耗时=%.2f秒", elapsed)
        except Exception as e:
            logger.error("ChromaDB 客户端初始化失败: %s", e)
            raise
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
