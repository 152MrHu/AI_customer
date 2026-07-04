"""文档 SQL 操作"""
from typing import Optional

from common.database import DB, fetchone, fetchall


async def insert_document(
    kb_id: int,
    file_name: str,
    file_type: str,
    file_size: int,
    file_path: str,
) -> int:
    """插入文档记录，返回 document_id"""
    async with DB() as db:
        await db.execute(
            "INSERT INTO documents (kb_id, file_name, file_type, file_size, file_path) "
            "VALUES (%s, %s, %s, %s, %s)",
            (kb_id, file_name, file_type, file_size, file_path),
        )
        return db.cur.lastrowid


async def find_by_id(document_id: int) -> Optional[dict]:
    """按 ID 查询文档"""
    return await fetchone(
        "SELECT document_id, kb_id, file_name, file_type, file_size, file_path, "
        "status, chunk_count, created_at, processed_at "
        "FROM documents WHERE document_id = %s",
        (document_id,),
    )


async def find_by_name(kb_id: int, file_name: str) -> Optional[dict]:
    """查询同知识库内是否存在同名文件"""
    return await fetchone(
        "SELECT document_id, kb_id, file_name, file_type, file_size, file_path, "
        "status, chunk_count, created_at, processed_at "
        "FROM documents WHERE kb_id = %s AND file_name = %s",
        (kb_id, file_name),
    )


async def list_documents(
    kb_id: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
    offset: int = 0,
    limit: int = 10,
) -> list[dict]:
    """分页查询文档列表（支持关键词和状态过滤）"""
    sql = (
        "SELECT document_id, kb_id, file_name, file_type, file_size, file_path, "
        "status, chunk_count, created_at, processed_at "
        "FROM documents WHERE kb_id = %s"
    )
    args: list = [kb_id]
    if keyword:
        sql += " AND file_name LIKE %s"
        args.append(f"%{keyword}%")
    if status:
        sql += " AND status = %s"
        args.append(status)
    sql += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
    args.extend([limit, offset])
    return await fetchall(sql, tuple(args))


async def count_documents(
    kb_id: int,
    keyword: Optional[str] = None,
    status: Optional[str] = None,
) -> int:
    """文档总数（支持关键词和状态过滤）"""
    sql = "SELECT COUNT(*) AS cnt FROM documents WHERE kb_id = %s"
    args: list = [kb_id]
    if keyword:
        sql += " AND file_name LIKE %s"
        args.append(f"%{keyword}%")
    if status:
        sql += " AND status = %s"
        args.append(status)
    row = await fetchone(sql, tuple(args))
    return row["cnt"] if row else 0


async def update_status(
    document_id: int, status: str, chunk_count: Optional[int] = None
) -> int:
    """更新文档状态（和切片数）"""
    async with DB() as db:
        if chunk_count is not None:
            return await db.execute(
                "UPDATE documents SET status = %s, chunk_count = %s "
                "WHERE document_id = %s",
                (status, chunk_count, document_id),
            )
        return await db.execute(
            "UPDATE documents SET status = %s WHERE document_id = %s",
            (status, document_id),
        )


async def update_processed(document_id: int, chunk_count: int) -> int:
    """更新文档为已处理：status=ready, chunk_count, processed_at=NOW()"""
    async with DB() as db:
        return await db.execute(
            "UPDATE documents SET status = 'ready', chunk_count = %s, "
            "processed_at = NOW() WHERE document_id = %s",
            (chunk_count, document_id),
        )


async def delete_document(document_id: int) -> int:
    """物理删除文档记录"""
    async with DB() as db:
        return await db.execute(
            "DELETE FROM documents WHERE document_id = %s",
            (document_id,),
        )
