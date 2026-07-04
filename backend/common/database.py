"""MySQL 数据库连接池管理 - aiomysql 异步"""
import aiomysql
from typing import Any, Optional
from common.config import settings

_pool: Optional[aiomysql.Pool] = None


async def create_pool():
    """创建全局连接池，应用启动时调用"""
    global _pool
    _pool = await aiomysql.create_pool(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=True,
        minsize=2,
        maxsize=10,
        pool_recycle=3600,
    )


async def close_pool():
    """关闭连接池，应用关闭时调用"""
    global _pool
    if _pool:
        _pool.close()
        await _pool.wait_closed()
        _pool = None


def get_pool() -> aiomysql.Pool:
    if _pool is None:
        raise RuntimeError("数据库连接池未初始化，请先调用 create_pool()")
    return _pool


class DB:
    """数据库操作上下文管理器"""

    def __init__(self):
        self.conn = None
        self.cur = None

    async def __aenter__(self):
        self.conn = get_pool().acquire()
        self.conn = await self.conn.__aenter__()
        self.cur = await self.conn.cursor()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.cur:
            await self.cur.close()
        if self.conn:
            self.conn.close()

    async def execute(self, sql: str, args: tuple = None) -> int:
        """执行 INSERT/UPDATE/DELETE，返回 affected rows"""
        await self.cur.execute(sql, args)
        return self.cur.rowcount

    async def fetchone(self, sql: str, args: tuple = None) -> Optional[dict]:
        """查询单条记录，返回 dict"""
        await self.cur.execute(sql, args)
        row = await self.cur.fetchone()
        if row is None:
            return None
        cols = [d[0] for d in self.cur.description]
        return dict(zip(cols, row))

    async def fetchall(self, sql: str, args: tuple = None) -> list[dict]:
        """查询多条记录，返回 list[dict]"""
        await self.cur.execute(sql, args)
        rows = await self.cur.fetchall()
        cols = [d[0] for d in self.cur.description]
        return [dict(zip(cols, row)) for row in rows]


async def execute(sql: str, args: tuple = None) -> int:
    """快捷执行"""
    async with DB() as db:
        return await db.execute(sql, args)


async def fetchone(sql: str, args: tuple = None) -> Optional[dict]:
    """快捷查询单条"""
    async with DB() as db:
        return await db.fetchone(sql, args)


async def fetchall(sql: str, args: tuple = None) -> list[dict]:
    """快捷查询多条"""
    async with DB() as db:
        return await db.fetchall(sql, args)
