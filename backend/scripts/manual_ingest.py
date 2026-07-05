"""手动入库脚本 - 绕过 HTTP，直接调 ai_service embedding + 写 ChromaDB"""
import asyncio
import sys
import httpx

sys.path.insert(0, '.')

from common.config import settings
from common.database import create_pool, close_pool
from common.logging_config import setup_logger
from knowledge_service.repositories import document_repo, kb_repo
from knowledge_service.parser.text_parser import parse_text
from knowledge_service.parser.chunker import chunk_text
from knowledge_service.vector_store import add_chunks

logger = setup_logger("manual_ingest")


async def manual_ingest(document_id: int):
    """手动入库：解析→切块→直接调 ai_service→写 ChromaDB"""
    await create_pool()

    doc = await document_repo.find_by_id(document_id)
    if not doc:
        logger.error("文档不存在: document_id=%s", document_id)
        return

    logger.info("开始入库: document_id=%s, file=%s", document_id, doc["file_name"])

    # 1. 解析文本
    text = await parse_text(doc["file_path"])
    logger.info("文本已解析, 长度=%d", len(text))

    # 2. 切块
    chunks = chunk_text(text, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    if not chunks:
        logger.warning("文档内容为空")
        return
    logger.info("已切块: %d chunks", len(chunks))

    # 3. 直接用 httpx 调 ai_service embedding（不用全局 client，新建一个）
    async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=5.0)) as client:
        resp = await client.post(
            f"{settings.AI_SERVICE_URL}/api/ai/embedding",
            json={"texts": chunks, "kb_id": doc["kb_id"]},
        )
        data = resp.json()
        if data.get("code") != 200:
            raise Exception(f"Embedding failed: {data.get('message')}")
        embeddings = data["data"]["embeddings"]
    logger.info("向量化完成: %d vectors", len(embeddings))

    # 4. 写 ChromaDB
    add_chunks(
        kb_id=doc["kb_id"],
        chunks=chunks,
        embeddings=embeddings,
        document_id=doc["document_id"],
        file_name=doc["file_name"],
    )

    # 5. 更新状态
    await document_repo.update_processed(document_id, len(chunks))
    await kb_repo.update_document_count(doc["kb_id"], 1)

    logger.info("入库完成: document_id=%s, chunks=%d", document_id, len(chunks))
    await close_pool()


if __name__ == "__main__":
    doc_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    asyncio.run(manual_ingest(doc_id))
