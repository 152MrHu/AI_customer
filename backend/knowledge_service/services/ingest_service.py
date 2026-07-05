"""异步入库服务：解析→切块→向量化→写ChromaDB→更新状态

安全设计（v2 - 完全隔离）：
- ingest 在独立 daemon 线程中运行，拥有自己的事件循环和数据库连接池
- 即使 ingest 永久阻塞，也不会拖死主 FastAPI 服务
- 每次入库有整体超时保护 (120s)
- ChromaDB 同步操作通过 asyncio.to_thread 放到线程池执行
- 任何步骤失败都标记 status=failed，不影响主服务
"""
import asyncio
import threading
from pathlib import Path

from common.config import settings
from common.logging_config import get_logger
from common.database import create_pool, close_pool, DB

from ..parser.text_parser import parse_text
from ..parser.pdf_parser import parse_pdf
from ..parser.docx_parser import parse_docx
from ..parser.md_parser import parse_md
from ..parser.csv_parser import parse_csv
from ..parser.chunker import chunk_text
from ..vector_store import add_chunks
from ..clients.ai_client import get_embeddings
from ..repositories import document_repo as _doc_repo_module, kb_repo as _kb_repo_module

logger = get_logger()

# 入库整体超时（秒）
INGEST_TIMEOUT = 120

# 全局 ingest 线程（daemon，主进程退出时自动终止）
_ingest_thread = None
_ingest_loop = None


def _get_ingest_loop():
    """获取 ingest 线程的事件循环"""
    return _ingest_loop


async def _parse_document(file_path: str, file_type: str) -> str:
    """根据文件类型选择解析器"""
    if file_type == "txt":
        return await parse_text(file_path)
    elif file_type == "pdf":
        return await parse_pdf(file_path)
    elif file_type == "docx":
        return await parse_docx(file_path)
    elif file_type == "md":
        return await parse_md(file_path)
    elif file_type == "csv":
        return await parse_csv(file_path)
    else:
        raise ValueError(f"不支持的文件类型: {file_type}")


async def _do_ingest(document_id: int):
    """实际入库逻辑（在 ingest 线程的事件循环中运行）"""
    # 1. 获取文档信息（使用独立连接池）
    async with DB() as db:
        doc = await db.fetchone(
            "SELECT document_id AS doc_id, kb_id, file_name AS doc_name, "
            "file_type AS doc_type, file_path, status "
            "FROM documents WHERE document_id = %s",
            (document_id,),
        )
    if not doc:
        logger.error("文档不存在: document_id=%s", document_id)
        return

    doc_name = doc.get("doc_name") or doc.get("file_name", "")
    logger.info("开始入库: document_id=%s, file=%s", document_id, doc_name)

    # 2. 按类型解析文本
    file_type = doc.get("doc_type") or doc.get("file_type", "")
    text = await _parse_document(doc["file_path"], file_type)

    # 3. 切块
    chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks:
        logger.warning("文档内容为空，无切块: document_id=%s", document_id)
        async with DB() as db:
            await db.execute("UPDATE documents SET status='failed' WHERE document_id=%s", (document_id,))
        return

    logger.info(
        "文档已切块: document_id=%s, chunks=%d, chunk_size=%d",
        document_id, len(chunks), settings.CHUNK_SIZE,
    )

    # 4. 调用 ai-service 向量化
    embeddings = await get_embeddings(chunks, doc["kb_id"])

    # 5. 写 ChromaDB（同步操作，放在线程中执行防止阻塞事件循环）
    await asyncio.to_thread(
        add_chunks,
        kb_id=doc["kb_id"],
        chunks=chunks,
        embeddings=embeddings,
        document_id=doc.get("doc_id") or doc.get("document_id", document_id),
        file_name=doc_name,
    )

    # 6. 更新状态 ready + chunk_count（使用独立连接池）
    async with DB() as db:
        await db.execute(
            "UPDATE documents SET status='ready', chunk_count=%s, processed_at=NOW() WHERE document_id=%s",
            (len(chunks), document_id),
        )
    async with DB() as db:
        await db.execute(
            "UPDATE knowledge_bases SET document_count = document_count + 1 WHERE kb_id = %s",
            (doc["kb_id"],),
        )

    logger.info("入库完成: document_id=%s, chunks=%d", document_id, len(chunks))


async def _ingest_with_timeout(document_id: int):
    """带超时保护的入库流程"""
    try:
        await asyncio.wait_for(_do_ingest(document_id), timeout=INGEST_TIMEOUT)
    except asyncio.TimeoutError:
        logger.error("入库超时(%ds): document_id=%s", INGEST_TIMEOUT, document_id)
        try:
            async with DB() as db:
                await db.execute("UPDATE documents SET status='failed' WHERE document_id=%s", (document_id,))
        except Exception:
            pass
    except Exception as e:
        logger.error("入库失败: document_id=%s, error=%s", document_id, e, exc_info=True)
        try:
            async with DB() as db:
                await db.execute("UPDATE documents SET status='failed' WHERE document_id=%s", (document_id,))
        except Exception:
            pass


def _ingest_thread_main():
    """ingest daemon 线程的主函数：创建独立事件循环和数据库连接池"""
    global _ingest_loop
    _ingest_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_ingest_loop)

    try:
        # 在独立线程中创建数据库连接池
        _ingest_loop.run_until_complete(create_pool())
        logger.info("Ingest 线程: 数据库连接池已初始化")

        # 线程事件循环持续运行，等待 ingest 任务
        _ingest_loop.run_forever()
    except Exception as e:
        logger.error("Ingest 线程异常退出: %s", e)
    finally:
        # 清理
        try:
            _ingest_loop.run_until_complete(close_pool())
        except Exception:
            pass
        _ingest_loop.close()
        _ingest_loop = None


def _start_ingest_thread():
    """启动 ingest daemon 线程（如果尚未启动）"""
    global _ingest_thread
    if _ingest_thread is None or not _ingest_thread.is_alive():
        _ingest_thread = threading.Thread(
            target=_ingest_thread_main,
            name="ingest-worker",
            daemon=True,  # 主进程退出时自动终止
        )
        _ingest_thread.start()
        logger.info("Ingest daemon 线程已启动")


def schedule_ingest(document_id: int):
    """调度入库任务：在 ingest 线程的事件循环中异步执行。

    与 asyncio.create_task 不同，此方法将任务提交到独立线程的事件循环，
    确保 ingest 过程完全不占用主 FastAPI 事件循环的资源。
    即使 ingest 挂起/阻塞，主服务仍能正常响应请求。
    """
    _start_ingest_thread()
    loop = _get_ingest_loop()
    if loop is None:
        logger.error("Ingest 线程事件循环不可用，无法入库: document_id=%s", document_id)
        return
    asyncio.run_coroutine_threadsafe(_ingest_with_timeout(document_id), loop)
    logger.info("入库任务已提交到 ingest 线程: document_id=%s", document_id)
