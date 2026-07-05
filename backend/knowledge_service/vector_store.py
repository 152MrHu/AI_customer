"""ChromaDB 向量存储封装（子进程隔离版 v4）

彻底解决 ChromaDB 在 Windows 上 hang 死主进程的问题：
- 所有 ChromaDB 操作都在**独立子进程**中执行
- 通过 subprocess.run() 调用 chroma_worker.py
- 带 timeout 自动终止 hang 的子进程
- 主进程完全不 import chromadb，不创建 PersistentClient

knowledge-service 负责写入/读取，ai-service 通过 HTTP 远程调用。
"""
import json
import os
import subprocess
import sys
import tempfile

from common.config import settings
from common.logging_config import get_logger

logger = get_logger()

# 子进程操作超时（秒）
_SUBPROCESS_TIMEOUT = 30


def _get_backend_dir() -> str:
    """获取 backend 目录的绝对路径（chroma_worker.py 需要 import common）"""
    # vector_store.py 在 backend/knowledge_service/ 下，backend 是其父目录
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_worker_script() -> str:
    """获取 chroma_worker.py 的绝对路径"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "chroma_worker.py")


def _subprocess_env() -> dict:
    """子进程环境变量：添加 backend 目录到 PYTHONPATH，确保能 import common"""
    backend_dir = _get_backend_dir()
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    existing_path = env.get("PYTHONPATH", "")
    if backend_dir not in existing_path:
        env["PYTHONPATH"] = f"{backend_dir};{existing_path}" if existing_path else backend_dir
    return env


def _run_worker(args: list, timeout: float = _SUBPROCESS_TIMEOUT) -> bool:
    """在子进程中运行 ChromaDB 写入/删除操作，返回是否成功"""
    worker = _get_worker_script()
    cmd = [sys.executable, worker] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_get_backend_dir(),
            env=_subprocess_env(),
        )
        if result.returncode == 0:
            return True
        else:
            stderr = (result.stderr or "").strip()
            logger.warning(
                "ChromaDB 子进程返回非零: cmd=%s, rc=%s, stderr=%s",
                " ".join(cmd), result.returncode, stderr[:500],
            )
            return False
    except subprocess.TimeoutExpired:
        logger.error("ChromaDB 子进程超时(%ds): cmd=%s", timeout, " ".join(cmd))
        return False
    except Exception as e:
        logger.error("ChromaDB 子进程异常: cmd=%s, error=%s", " ".join(cmd), e)
        return False


def _run_worker_with_result(args: list, timeout: float = _SUBPROCESS_TIMEOUT) -> dict | None:
    """在子进程中运行 ChromaDB 读取操作，解析 stdout JSON 返回结果"""
    worker = _get_worker_script()
    cmd = [sys.executable, worker] + args

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=_get_backend_dir(),
            env=_subprocess_env(),
        )
        if result.returncode == 0 and result.stdout:
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                logger.warning("ChromaDB 子进程输出无法解析为 JSON: %s", result.stdout[:200])
                return None
        else:
            stderr = (result.stderr or "").strip()
            logger.warning(
                "ChromaDB 子进程读取失败: cmd=%s, rc=%s, stderr=%s",
                " ".join(cmd), result.returncode, stderr[:500],
            )
            return None
    except subprocess.TimeoutExpired:
        logger.error("ChromaDB 子进程读取超时(%ds): cmd=%s", timeout, " ".join(cmd))
        return None
    except Exception as e:
        logger.error("ChromaDB 子进程读取异常: cmd=%s, error=%s", " ".join(cmd), e)
        return None


def create_collection(kb_id: int):
    """创建知识库 collection（子进程中执行）"""
    ok = _run_worker(["create_collection", str(kb_id)])
    if ok:
        logger.info("ChromaDB collection 已创建: kb_%s", kb_id)
    else:
        logger.warning("ChromaDB collection 创建失败: kb_%s", kb_id)


def add_chunks(
    kb_id: int,
    chunks: list[str],
    embeddings: list[list[float]],
    document_id: int,
    file_name: str,
):
    """写入向量数据（子进程中执行）

    将 chunks 和 embeddings 序列化为临时 JSON 文件传给子进程，
    避免命令行参数过长的问题。
    """
    data = {
        "chunks": chunks,
        "embeddings": embeddings,
        "document_id": document_id,
        "file_name": file_name,
    }

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="chroma_")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        timeout = max(_SUBPROCESS_TIMEOUT, min(60.0, len(chunks) * 3))
        ok = _run_worker(["add", str(kb_id), tmp_path], timeout=timeout)

        if ok:
            logger.info(
                "ChromaDB 写入完成: kb_%s, document_id=%s, chunks=%d",
                kb_id, document_id, len(chunks),
            )
        else:
            logger.error(
                "ChromaDB 写入失败: kb_%s, document_id=%s",
                kb_id, document_id,
            )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def delete_by_document(kb_id: int, document_id: int):
    """按文档 ID 删除向量（子进程中执行）"""
    ok = _run_worker(["delete_by_doc", str(kb_id), str(document_id)])
    if ok:
        logger.info("ChromaDB 删除完成: kb_%s, document_id=%s", kb_id, document_id)
    else:
        logger.warning("ChromaDB 删除失败(非致命): kb_%s, document_id=%s", kb_id, document_id)


def delete_collection(kb_id: int):
    """删除整个知识库的 collection（子进程中执行）"""
    ok = _run_worker(["delete_collection", str(kb_id)])
    if ok:
        logger.info("ChromaDB collection 已删除: kb_%s", kb_id)
    else:
        logger.warning("ChromaDB collection 删除失败: kb_%s", kb_id)


def search(kb_id: int, query_embedding: list[float], top_k: int = 5) -> list[dict]:
    """向量检索（子进程中执行），返回检索结果列表"""
    data = {
        "kb_id": kb_id,
        "query_embedding": query_embedding,
        "top_k": top_k,
    }

    tmp_fd, tmp_path = tempfile.mkstemp(suffix=".json", prefix="chroma_search_")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

        result = _run_worker_with_result(["search", tmp_path], timeout=_SUBPROCESS_TIMEOUT)

        if result and result.get("status") == "ok":
            return result.get("items", [])
        return []
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def count(kb_id: int) -> int:
    """查询向量数量（子进程中执行）"""
    result = _run_worker_with_result(["count", str(kb_id)], timeout=_SUBPROCESS_TIMEOUT)

    if result and result.get("status") == "ok":
        return result.get("count", 0)
    return 0
