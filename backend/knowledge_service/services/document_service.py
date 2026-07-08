"""文档服务"""
import re
from pathlib import Path
from typing import Optional

from fastapi import UploadFile

from common.response import ErrorCode
from common.exceptions import BusinessError
from common.logging_config import get_logger
from common.pagination import PageParams

from ..repositories import document_repo, kb_repo
from ..vector_store import delete_by_document
from .ingest_service import schedule_ingest
from .kb_service import check_kb_ownership

logger = get_logger()

# 支持的文件格式及其 magic bytes
ALLOWED_EXTENSIONS = {"txt", "pdf", "docx", "md", "csv"}
MAGIC_BYTES = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",  # DOCX 是 ZIP 格式
}
# 文件大小限制 20MB
MAX_FILE_SIZE = 20 * 1024 * 1024


def _sanitize_filename(filename: str) -> str:
    """清洗文件名：移除路径遍历字符和危险字符，生成安全的文件名"""
    # 移除路径分隔符和空字节
    sanitized = filename.replace("\\", "_").replace("/", "_").replace("\x00", "")
    # 只保留安全字符：字母、数字、中文、下划线、连字符、点
    sanitized = re.sub(r"[^\w一-鿿.\- ]", "_", sanitized)
    # 去除首尾空白和点（Windows 不允许文件名以点结尾）
    sanitized = sanitized.strip(" .")
    # 防止空文件名
    if not sanitized or sanitized.startswith("."):
        sanitized = f"uploaded_{sanitized}"
    if not sanitized:
        sanitized = "unnamed_file"
    # 限制文件名长度
    if len(sanitized) > 200:
        name, ext = (sanitized.rsplit(".", 1) + [""])[:2]
        sanitized = f"{name[:195]}.{ext}" if ext else name[:200]
    return sanitized


def _validate_magic_bytes(file_ext: str, content: bytes) -> None:
    """校验文件魔数（magic bytes）是否与扩展名匹配"""
    expected = MAGIC_BYTES.get(file_ext)
    if expected is None:
        return  # txt, md, csv 无固定魔数，跳过
    if not content.startswith(expected):
        raise BusinessError(
            ErrorCode.PARAM_ERROR,
            f"文件内容与扩展名 .{file_ext} 不匹配，上传被拒绝",
        )


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
    raw_name = file.filename or ""
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise BusinessError(ErrorCode.DOC_FORMAT_UNSUPPORTED, "仅支持 pdf/txt/docx/md/csv 格式")

    # 读取文件内容并校验大小
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise BusinessError(ErrorCode.FILE_TOO_LARGE, "文件大小不能超过 20MB")

    # 校验魔数（防止伪造扩展名）
    _validate_magic_bytes(ext, content)

    # 清洗文件名（防路径遍历）
    file_name = _sanitize_filename(raw_name)
    logger.info("文件名清洗: %s -> %s", raw_name, file_name)

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

    # 触发异步入库（在主事件循环中创建后台 task）
    schedule_ingest(document_id)
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


async def delete_document(document_id: int, user_id: int = None, role: str = "user"):
    """删除文档（需校验文档所属知识库的所有权）：

    重要：只有 status == 'ready' 的文档才清理向量数据，
    因为 pending/failed 状态的文档从未成功写入过向量数据。

    删除步骤（ready 文档）：
    1. 校验所有权（知识库 owner 或 admin）
    2. 清理向量数据（SQLite + numpy，不会 segfault）
    3. 删除数据库记录
    4. 更新知识库 document_count - 1
    5. 删除物理文件

    删除步骤（非 ready 文档）：
    1. 校验所有权
    2. 跳过向量清理（无向量数据）
    3. 删除数据库记录
    4. 删除物理文件
    """
    doc = await document_repo.find_by_id(document_id)
    if not doc:
        raise BusinessError(ErrorCode.NOT_FOUND, "文档不存在")

    # 校验知识库所有权
    await check_kb_ownership(doc["kb_id"], user_id, role)

    kb_id = doc["kb_id"]
    status = doc["status"]
    file_path = doc.get("file_path")

    # 1. 仅当文档状态为 ready 时才清理向量数据
    if status == "ready":
        delete_by_document(kb_id, document_id)
    else:
        logger.info(
            "跳过向量数据清理(文档状态为 %s): document_id=%s",
            status, document_id,
        )

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
