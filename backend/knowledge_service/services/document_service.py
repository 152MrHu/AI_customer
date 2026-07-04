"""文档服务"""
import asyncio
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from common.response import ErrorCode
from common.exceptions import BusinessError
from common.logging_config import get_logger
from common.pagination import PageParams

from ..repositories import document_repo, kb_repo
from ..vector_store import delete_by_document
from . import ingest_service

logger = get_logger()

# 支持的文件格式
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx"}
# 文件大小限制 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024


async def upload_document(kb_id: int, file: UploadFile, upload_dir: Path) -> dict:
    """上传文档：
    1. 校验文件格式和大小
    2. 检查同知识库文件名唯一
    3. 保存文件
    4. 创建数据库记录（status=pending）
    5. 触发异步入库
    """
    # 校验知识库是否存在
    kb = await kb_repo.find_by_id(kb_id)
    if not kb:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")

    # 校验文件格式
    file_name = file.filename or ""
    ext = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessError(ErrorCode.DOC_FORMAT_UNSUPPORTED, "仅支持 pdf/txt/docx 格式")

    # 读取文件内容并校验大小
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise BusinessError(ErrorCode.FILE_TOO_LARGE, "文件大小不能超过 20MB")

    # 检查同知识库文件名唯一
    existing = await document_repo.find_by_name(kb_id, file_name)
    if existing:
        raise BusinessError(ErrorCode.KB_NAME_EXISTS, "该知识库下已存在同名文件")

    # 保存文件到 upload_dir/kb_{kb_id}/
    kb_upload_dir = upload_dir / f"kb_{kb_id}"
    kb_upload_dir.mkdir(parents=True, exist_ok=True)
    file_path = kb_upload_dir / file_name
    file_path.write_bytes(content)

    # 创建数据库记录
    document_id = await document_repo.insert_document(
        kb_id=kb_id,
        file_name=file_name,
        file_type=ext,
        file_size=file_size,
        file_path=str(file_path),
    )

    # 触发异步入库（不阻塞响应）
    asyncio.create_task(ingest_service.ingest(document_id))
    logger.info("文档已上传，异步入库已触发: document_id=%s", document_id)

    # 返回文档信息
    doc = await document_repo.find_by_id(document_id)
    return doc


async def list_documents(
    kb_id: int,
    keyword: Optional[str],
    status: Optional[str],
    page_params: PageParams,
) -> dict:
    """分页查询文档列表"""
    total = await document_repo.count_documents(kb_id, keyword, status)
    items = await document_repo.list_documents(
        kb_id, keyword, status, page_params.offset, page_params.limit,
    )
    return {"total": total, "items": items}


async def delete_document(document_id: int):
    """删除文档：
    1. 清理 ChromaDB 向量
    2. 删除数据库记录
    3. 更新知识库 document_count - 1
    4. 删除物理文件
    """
    doc = await document_repo.find_by_id(document_id)
    if not doc:
        raise BusinessError(ErrorCode.NOT_FOUND, "文档不存在")

    kb_id = doc["kb_id"]
    status = doc["status"]
    file_path = doc.get("file_path")

    # 1. 清理 ChromaDB 向量
    try:
        delete_by_document(kb_id, document_id)
    except Exception as e:
        logger.warning("清理 ChromaDB 向量失败: document_id=%s, error=%s", document_id, e)

    # 2. 删除数据库记录
    await document_repo.delete_document(document_id)

    # 3. 更新知识库文档计数（仅当文档已入库成功时才递减）
    if status == "ready":
        await kb_repo.update_document_count(kb_id, -1)

    # 4. 删除物理文件
    if file_path:
        try:
            path = Path(file_path)
            if path.exists():
                path.unlink()
        except Exception as e:
            logger.warning("删除物理文件失败: %s, error=%s", file_path, e)
