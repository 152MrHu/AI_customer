"""异步入库服务：解析→切块→向量化→写ChromaDB→更新状态"""
from common.config import settings
from common.logging_config import get_logger

from ..repositories import document_repo, kb_repo
from ..parser.text_parser import parse_text
from ..parser.pdf_parser import parse_pdf
from ..parser.docx_parser import parse_docx
from ..parser.md_parser import parse_md
from ..parser.csv_parser import parse_csv
from ..parser.chunker import chunk_text
from ..vector_store import add_chunks
from ..clients.ai_client import get_embeddings

logger = get_logger()


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


async def ingest(document_id: int):
    """异步入库：解析→切块→向量化→写ChromaDB→更新状态"""
    try:
        # 1. 获取文档信息
        doc = await document_repo.find_by_id(document_id)
        if not doc:
            logger.error("文档不存在: document_id=%s", document_id)
            return

        logger.info("开始入库: document_id=%s, file=%s", document_id, doc.get("doc_name") or doc.get("file_name"))

        # 2. 按类型解析文本
        text = await _parse_document(doc["file_path"], doc.get("doc_type") or doc.get("file_type"))

        # 3. 切块
        chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
        if not chunks:
            logger.warning("文档内容为空，无切块: document_id=%s", document_id)
            await document_repo.update_status(document_id, "failed")
            return

        logger.info(
            "文档已切块: document_id=%s, chunks=%d, chunk_size=%d",
            document_id, len(chunks), settings.CHUNK_SIZE,
        )

        # 4. 调用 ai-service 向量化
        embeddings = await get_embeddings(chunks, doc["kb_id"])

        # 5. 写 ChromaDB（同步操作，放在线程中执行防止阻塞事件循环）
        import asyncio
        await asyncio.to_thread(
            add_chunks,
            kb_id=doc["kb_id"],
            chunks=chunks,
            embeddings=embeddings,
            document_id=doc.get("doc_id") or doc.get("document_id", document_id),
            file_name=doc.get("doc_name") or doc.get("file_name"),
        )

        # 6. 更新状态 ready
        await document_repo.update_processed(document_id, len(chunks))
        await kb_repo.update_document_count(doc["kb_id"], 1)

        logger.info("入库完成: document_id=%s, chunks=%d", document_id, len(chunks))

    except Exception as e:
        logger.error("入库失败: document_id=%s, error=%s", document_id, e, exc_info=True)
        await document_repo.update_status(document_id, "failed")
