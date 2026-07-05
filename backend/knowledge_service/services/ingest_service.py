"""异步入库服务：解析→切块→向量化→写ChromaDB→更新状态

安全设计（v3 - 主事件循环 + 多层防护）：
- 使用 asyncio.create_task() 在主事件循环中运行（不再使用独立线程）
- 原因：独立线程的 create_pool() 会覆盖 database.py 全局 _pool，
  导致主线程 DB 操作拿到绑定到错误事件循环的 pool → "attached to a different loop"
- 三层防护确保不拖死主服务：
  1. ChromaDB 同步操作通过 asyncio.to_thread 放到线程池，且有 chroma_lock 串行化
  2. HTTP 调用使用独立 httpx client（60s 超时）
  3. 整体入库有 wait_for(120s) 超时保护
"""
import asyncio
from pathlib import Path

from common.config import settings
from common.logging_config import get_logger
# 使用主服务的数据库连接池（同一个事件循环，不存在 loop 冲突）
from common.database import DB

from ..parser.text_parser import parse_text
from ..parser.pdf_parser import parse_pdf
from ..parser.docx_parser import parse_docx
from ..parser.md_parser import parse_md
from ..parser.csv_parser import parse_csv
from ..parser.chunker import chunk_text
from ..vector_store import add_chunks
from ..clients.ai_client import get_embeddings

logger = get_logger()

# 入库整体超时（秒）
INGEST_TIMEOUT = 120


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
    """实际入库逻辑（在主事件循环中作为 task 运行）"""
    # 1. 获取文档信息（使用主服务的连接池）
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

    # 6. 更新状态 ready + chunk_count（使用主服务连接池）
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


def schedule_ingest(document_id: int):
    """调度入库任务：在主事件循环中创建后台 task。

    v3 改进：不再使用独立 daemon 线程。
    原因：独立线程调用 create_pool() 会覆盖 database.py 的全局 _pool 变量，
    导致主线程的 DB 操作使用了绑定到错误事件循环的连接池，
    触发 "attached to a different loop" 错误。

    防护措施（确保不拖死主服务）：
    - ChromaDB 操作通过 asyncio.to_thread() 在线程池执行，且有 chroma_lock 串行化
    - HTTP 调用(ai_client)使用独立 httpx client + 60s 超时
    - 整体入库流程有 wait_for(120s) 超时保护
    """
    # 创建后台 task，不 await，让它在主事件循环中异步运行
    task = asyncio.create_task(_ingest_with_timeout(document_id))
    logger.info(
        "入库任务已创建(主事件循环task): document_id=%s, task_id=%s",
        document_id, id(task),
    )
