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


async def check_kb_ownership(kb_id: int, user_id: int, role: str):
    """校验知识库所有权：owner 本人或 admin 可操作，否则抛出异常"""
    if role == "admin":
        return
    kb = await kb_repo.find_by_id(kb_id)
    if not kb:
        raise BusinessError(ErrorCode.NOT_FOUND, "知识库不存在")
    if kb.get("owner_id") != user_id:
        raise BusinessError(ErrorCode.FORBIDDEN, "无权操作此知识库，只能操作自己创建的知识库")


async def create_kb(data: dict, owner_id: int = None) -> dict:
    """创建知识库：
    1. 检查名称唯一
    2. 插入数据库（含 owner_id）
    3. 创建向量存储 collection
    owner_id=None → 管理员创建（公共），owner_id=用户ID → 私有
    """
    name = data["name"]
    description = data.get("description")

    # 检查名称唯一
    existing = await kb_repo.find_by_name(name)
    if existing:
        raise BusinessError(ErrorCode.KB_NAME_EXISTS, "知识库名称已存在")

    # 插入数据库
    kb_id = await kb_repo.insert_kb(name, description, owner_id)

    # 创建向量存储 collection（SQLite 自动创建，始终成功）
    create_collection(kb_id)

    # 返回完整信息
    kb = await kb_repo.find_by_id(kb_id)
    return kb


async def delete_kb(kb_id: int, user_id: int = None, role: str = "user"):
    """删除知识库（需校验所有权）：
    1. 校验所有权（owner 或 admin）
    2. 删除向量存储
    3. 删除文档记录+文件
    4. 删除知识库记录
    """
    await check_kb_ownership(kb_id, user_id, role)
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


async def list_available_kbs(user_id: int = None, role: str = "user") -> list[dict]:
    """获取可用知识库的简要列表（供用户选择知识库时使用）
    - admin：返回全部
    - 普通用户/客服：返回公共知识库(owner_id IS NULL) + 自己创建的
    """
    if role == "admin":
        items = await kb_repo.list_available_kbs(None)
    else:
        items = await kb_repo.list_available_kbs(user_id)
    return [{
        "kb_id": item["kb_id"],
        "name": item["name"],
        "description": item.get("description"),
        "owner_id": item.get("owner_id"),
        "document_count": item.get("document_count", 0),
        "created_at": str(item["created_at"]) if item.get("created_at") else None,
        "updated_at": str(item["updated_at"]) if item.get("updated_at") else None,
    } for item in items]
