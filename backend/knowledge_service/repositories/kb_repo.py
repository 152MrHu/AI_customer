"""知识库 SQL 操作"""
from typing import Optional

from common.database import DB, fetchone, fetchall


async def insert_kb(name: str, description: Optional[str] = None, owner_id: Optional[int] = None) -> int:
    """插入知识库，返回 kb_id。owner_id=None 表示管理员创建（公共）"""
    async with DB() as db:
        await db.execute(
            "INSERT INTO knowledge_bases (name, description, owner_id) VALUES (%s, %s, %s)",
            (name, description, owner_id),
        )
        return db.cur.lastrowid


async def find_by_name(name: str) -> Optional[dict]:
    """按名称查询知识库"""
    return await fetchone(
        "SELECT kb_id, name, description, owner_id, document_count, created_at, updated_at "
        "FROM knowledge_bases WHERE name = %s",
        (name,),
    )


async def find_by_id(kb_id: int) -> Optional[dict]:
    """按 ID 查询知识库"""
    return await fetchone(
        "SELECT kb_id, name, description, owner_id, document_count, created_at, updated_at "
        "FROM knowledge_bases WHERE kb_id = %s",
        (kb_id,),
    )


async def list_kbs(offset: int, limit: int) -> list[dict]:
    """分页查询知识库列表"""
    return await fetchall(
        "SELECT kb_id, name, description, owner_id, document_count, created_at, updated_at "
        "FROM knowledge_bases ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )


async def list_available_kbs(user_id: int = None) -> list[dict]:
    """获取可用知识库列表：公共(owner_id IS NULL) + 当前用户自己的。
    若 user_id 为 None（管理员），返回全部。
    """
    if user_id is None:
        return await fetchall(
            "SELECT kb_id, name, description, owner_id, document_count, created_at, updated_at "
            "FROM knowledge_bases ORDER BY created_at DESC"
        )
    return await fetchall(
        "SELECT kb_id, name, description, owner_id, document_count, created_at, updated_at "
        "FROM knowledge_bases "
        "WHERE owner_id IS NULL OR owner_id = %s ORDER BY created_at DESC",
        (user_id,),
    )


async def count_kbs() -> int:
    """知识库总数"""
    row = await fetchone("SELECT COUNT(*) AS cnt FROM knowledge_bases")
    return row["cnt"] if row else 0


async def update_document_count(kb_id: int, delta: int) -> int:
    """增量更新文档数量 document_count += delta"""
    async with DB() as db:
        return await db.execute(
            "UPDATE knowledge_bases SET document_count = document_count + %s WHERE kb_id = %s",
            (delta, kb_id),
        )


async def delete_kb(kb_id: int) -> int:
    """删除知识库记录"""
    async with DB() as db:
        return await db.execute(
            "DELETE FROM knowledge_bases WHERE kb_id = %s",
            (kb_id,),
        )
