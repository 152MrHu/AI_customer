"""知识库服务"""
import asyncio

from common.response import ErrorCode
from common.exceptions import BusinessError
from common.pagination import PageParams
from common.logging_config import get_logger

from ..repositories import kb_repo
from ..vector_store import create_collection

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

    # 创建 ChromaDB collection（同步操作放在线程中）
    try:
        await asyncio.to_thread(create_collection, kb_id)
    except Exception as e:
        # ChromaDB 创建失败不影响数据库记录，后续入库时会重试
        logger.warning("ChromaDB collection 创建失败(kb_id=%s): %s", kb_id, e)

    # 返回完整信息
    kb = await kb_repo.find_by_id(kb_id)
    return kb


async def list_kbs(page_params: PageParams) -> dict:
    """分页查询知识库列表"""
    total = await kb_repo.count_kbs()
    items = await kb_repo.list_kbs(page_params.offset, page_params.page_size)
    return {"total": total, "items": items}
