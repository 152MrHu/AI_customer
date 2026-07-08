"""知识库服务"""
from pathlib import Path

from common.config import settings
from common.response import ErrorCode
from common.exceptions import BusinessError
from common.pagination import PageParams
from common.logging_config import get_logger

from ..repositories import kb_repo, document_repo
from ..vector_store import create_collection, delete_collection

logger = get_logger()


async def create_kb(data: dict) -> dict:
    """创建知识库：
    1. 检查名称唯一
    2. 插入数据库
    3. 异步创建 ChromaDB collection（放在线程中防止阻塞事件循环）
    """
    name = data["name"]
    description = data.get("description")

    # 检查名称唯一
    existing = await kb_repo.find_by_name(name)
    if existing:
        raise BusinessError(ErrorCode.KB_NAME_EXISTS, "知识库名称已存在")

    # 插入数据库
    kb_id = await kb_repo.insert_kb(name, description)

    # 创建向量存储 collection（SQLite 自动创建，始终成功）
    create_collection(kb_id)

    # 返回完整信息
    kb = await kb_repo.find_by_id(kb_id)
    return kb


async def delete_kb(kb_id: int):
    """删除知识库：
    1. 删除 ChromaDB collection（放在线程中）
    2. 删除所有文档数据库记录
    3. 删除所有物理文件
    4. 删除知识库数据库记录
    """
    kb = await kb_repo.find_by_id(kb_id)
    if not kb:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")

    # 1. 删除向量存储 collection（SQLite DELETE，不会 segfault）
    delete_collection(kb_id)

    # 2. 获取所有文档记录（用于删除物理文件）
    docs = await document_repo.list_documents(kb_id, None, None, 0, 1000)

    # 3. 删除所有文档数据库记录
    from common.database import execute
    await execute("DELETE FROM documents WHERE kb_id = %s", (kb_id,))

    # 4. 删除物理文件和上传目录
    upload_dir = Path(settings.upload_dir_path) / f"kb_{kb_id}"
    if upload_dir.exists():
        try:
            # 删除目录下所有文件
            for doc in (docs or []):
                file_path = doc.get("file_path")
                if file_path:
                    try:
                        Path(file_path).unlink(missing_ok=True)
                    except Exception:
                        pass
            # 删除整个目录
            import shutil
            shutil.rmtree(upload_dir, ignore_errors=True)
        except Exception as e:
            logger.warning("删除上传目录失败: %s, %s", upload_dir, e)

    # 5. 删除知识库数据库记录
    await kb_repo.delete_kb(kb_id)
    logger.info("知识库已删除: kb_id=%s, name=%s", kb_id, kb.get("name"))


async def list_kbs(page_params: PageParams) -> dict:
    """分页查询知识库列表"""
    total = await kb_repo.count_kbs()
    items = await kb_repo.list_kbs(page_params.offset, page_params.page_size)
    return {"total": total, "items": items}


async def list_available_kbs() -> list[dict]:
    """获取所有可用知识库的简要列表（供用户选择知识库时使用）
    只返回 id 和 name，不包含文档数量等管理信息。
    不限制数量，返回全部（知识库数量通常很少）。
    """
    items = await kb_repo.list_kbs(0, 100)
    return [{"kb_id": item["kb_id"], "name": item["name"]} for item in items]
