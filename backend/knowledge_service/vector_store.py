"""轻量级向量存储 - SQLite + numpy 替代 ChromaDB

彻底解决 ChromaDB 1.x Rust 后端在 Python 3.13 + Windows 上的段错误问题。

设计原则：
- 所有向量数据存储在 SQLite 中（JSON 序列化 embeddings）
- 使用 numpy 计算余弦相似度（纯 Python/预编译 wheel，无 segfault 风险）
- 不依赖任何 Rust/C++ native 库（chromadb/hnswlib 都有兼容问题）
- 接口与原 vector_store.py 保持一致，上层代码无需修改

存储结构（SQLite 表 vec_chunks）：
- kb_id INTEGER       知识库 ID
- document_id INTEGER 文档 ID
- chunk_index INTEGER 切块索引
- file_name TEXT      文件名
- chunk_text TEXT     切块文本内容
- embedding TEXT      JSON 序列化的 embedding 向量（list[float]）
"""
import json
import sqlite3
import numpy as np
from pathlib import Path

from common.config import settings
from common.logging_config import get_logger

logger = get_logger()

# SQLite 数据库路径
_DB_PATH = Path(settings.CHROMA_PERSIST_PATH) / "vec_store.db"

# 确保目录存在
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def _get_conn() -> sqlite3.Connection:
    """获取 SQLite 连接"""
    conn = sqlite3.connect(str(_DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _ensure_table(conn: sqlite3.Connection):
    """确保 vec_chunks 表存在"""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vec_chunks (
            kb_id INTEGER NOT NULL,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            chunk_text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            PRIMARY KEY (kb_id, document_id, chunk_index)
        )
    """)
    conn.commit()


def create_collection(kb_id: int) -> bool:
    """创建知识库 collection（SQLite 中自动创建，始终成功）

    在纯 SQLite 方案中不需要单独创建 collection，
    数据插入时表会自动创建。此函数保留接口兼容性。
    """
    conn = _get_conn()
    _ensure_table(conn)
    conn.close()
    logger.info("向量存储 collection 就绪: kb_%s", kb_id)
    return True


def add_chunks(
    kb_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: int,
    file_name: str,
) -> bool:
    """写入向量数据到 SQLite

    Args:
        kb_id: 知识库 ID
        chunks: 切块文本列表
        embeddings: 对应的 embedding 向量列表
        document_id: 文档 ID
        file_name: 文件名

    Returns: True=成功, False=失败
    """
    if len(chunks) != len(embeddings):
        logger.error(
            "chunks 数量(%d)与 embeddings 数量(%d)不匹配: kb_%s, doc_%s",
            len(chunks), len(embeddings), kb_id, document_id,
        )
        return False

    conn = _get_conn()
    _ensure_table(conn)

    try:
        rows = []
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            rows.append((kb_id, document_id, i, file_name, chunk, json.dumps(emb)))

        conn.executemany(
            "INSERT OR REPLACE INTO vec_chunks (kb_id, document_id, chunk_index, file_name, chunk_text, embedding) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        logger.info(
            "向量写入完成: kb_%s, document_id=%s, chunks=%d",
            kb_id, document_id, len(chunks),
        )
        return True
    except Exception as e:
        logger.error("向量写入失败: kb_%s, document_id=%s, error=%s", kb_id, document_id, e)
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_by_document(kb_id: int, document_id: int) -> bool:
    """按文档 ID 删除向量数据"""
    conn = _get_conn()
    try:
        n = conn.execute(
            "DELETE FROM vec_chunks WHERE kb_id=? AND document_id=?",
            (kb_id, document_id),
        ).rowcount
        conn.commit()
        logger.info("向量删除完成: kb_%s, document_id=%s, deleted=%d", kb_id, document_id, n)
        return True
    except Exception as e:
        logger.warning("向量删除失败: kb_%s, document_id=%s, error=%s", kb_id, document_id, e)
        return False
    finally:
        conn.close()


def delete_collection(kb_id: int) -> bool:
    """删除整个知识库的向量数据"""
    conn = _get_conn()
    try:
        n = conn.execute("DELETE FROM vec_chunks WHERE kb_id=?", (kb_id,)).rowcount
        conn.commit()
        logger.info("向量 collection 删除完成: kb_%s, deleted=%d", kb_id, n)
        return True
    except Exception as e:
        logger.warning("向量 collection 删除失败: kb_%s, error=%s", kb_id, e)
        return False
    finally:
        conn.close()


def search(kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """向量检索：使用 numpy 余弦相似度

    Args:
        kb_id: 知识库 ID
        query_embedding: 查询向量
        top_k: 返回结果数量

    Returns: [{"doc_name", "score", "snippet", "document"}]
    """
    conn = _get_conn()
    _ensure_table(conn)

    try:
        rows = conn.execute(
            "SELECT document_id, chunk_index, file_name, chunk_text, embedding "
            "FROM vec_chunks WHERE kb_id=?",
            (kb_id,),
        ).fetchall()

        if not rows:
            return []

        # 将查询向量转为 numpy 数组
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        # 计算所有候选向量的余弦相似度
        candidates = []
        for row in rows:
            doc_id, chunk_idx, file_name, chunk_text, emb_json = row
            emb_vec = np.array(json.loads(emb_json), dtype=np.float32)
            emb_norm = np.linalg.norm(emb_vec)
            if emb_norm == 0:
                continue
            score = float(np.dot(query_vec, emb_vec) / (query_norm * emb_norm))
            candidates.append({
                "doc_name": file_name,
                "score": round(score, 4),
                "snippet": chunk_text[:200] if chunk_text else "",
                "document": chunk_text,
                "document_id": doc_id,
                "chunk_index": chunk_idx,
            })

        # 按相似度排序，取 top_k
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

    except Exception as e:
        logger.error("向量检索失败: kb_%s, error=%s", kb_id, e)
        return []
    finally:
        conn.close()


def count(kb_id: int) -> int:
    """查询向量数量"""
    conn = _get_conn()
    _ensure_table(conn)
    try:
        n = conn.execute(
            "SELECT COUNT(*) FROM vec_chunks WHERE kb_id=?",
            (kb_id,),
        ).fetchone()[0]
        return n
    except Exception:
        return 0
    finally:
        conn.close()
