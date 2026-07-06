"""数据库初始化脚本 - 执行 init.sql 建库建表"""
import asyncio
import os
import sys
from pathlib import Path

import aiomysql

# 添加 backend 目录到 sys.path 以便导入 common
sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import settings


async def init_database():
    """连接 MySQL 并执行 init.sql"""
    sql_file = Path(__file__).parent.parent / "sql" / "init.sql"
    sql_script = sql_file.read_text(encoding="utf-8")

    print(f"正在连接 MySQL {settings.MYSQL_HOST}:{settings.MYSQL_PORT} ...")

    conn = await aiomysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        charset="utf8mb4",
        autocommit=True,
    )

    try:
        async with conn.cursor() as cur:
            # 按分号分割并执行每条 SQL
            statements = [s.strip() for s in sql_script.split(";") if s.strip()]
            for stmt in statements:
                await cur.execute(stmt)
                print(f"  执行: {stmt[:60]}...")
        print("\n数据库初始化完成！")
        print(f"数据库: {settings.MYSQL_DATABASE}")
        print("已创建表: users, knowledge_bases, documents, sessions, messages, message_feedback, handoff_tickets")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(init_database())
