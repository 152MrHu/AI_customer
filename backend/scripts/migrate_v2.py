"""执行 v2.0 数据库迁移 — 检测并添加缺失的表和列，幂等安全"""
import asyncio
import sys
from pathlib import Path

import aiomysql

sys.path.insert(0, str(Path(__file__).parent.parent))
from common.config import settings


async def column_exists(cur, table: str, column: str) -> bool:
    """检查表中是否存在指定列"""
    await cur.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (settings.MYSQL_DATABASE, table, column),
    )
    row = await cur.fetchone()
    return row[0] > 0


async def table_exists(cur, table: str) -> bool:
    """检查表是否存在"""
    await cur.execute(
        "SELECT COUNT(*) AS cnt FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        (settings.MYSQL_DATABASE, table),
    )
    row = await cur.fetchone()
    return row[0] > 0


CREATE_FEEDBACK = """
CREATE TABLE IF NOT EXISTS message_feedback (
    feedback_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    rating TINYINT NOT NULL COMMENT '1=赞 0=踩',
    comment VARCHAR(500) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_msg_user (message_id, user_id),
    KEY idx_message_id (message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='消息反馈表'
"""

CREATE_HANDOFF = """
CREATE TABLE IF NOT EXISTS handoff_tickets (
    ticket_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    session_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    reason VARCHAR(500) DEFAULT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending' COMMENT 'pending/claimed/resolved/closed',
    claimed_by BIGINT DEFAULT NULL,
    resolution VARCHAR(1000) DEFAULT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    KEY idx_user_id (user_id),
    KEY idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='人工转接工单表'
"""


async def migrate():
    print(f"连接 MySQL {settings.MYSQL_HOST}:{settings.MYSQL_PORT} ...")
    conn = await aiomysql.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        db=settings.MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=True,
    )

    try:
        async with conn.cursor() as cur:
            # 1. sessions.mode 列
            if await column_exists(cur, "sessions", "mode"):
                print("  [跳过] sessions.mode 列已存在")
            else:
                await cur.execute(
                    "ALTER TABLE sessions ADD COLUMN mode VARCHAR(20) NOT NULL DEFAULT 'kb' AFTER kb_id"
                )
                print("  [完成] sessions 表添加 mode 列")

            # 2. message_feedback 表
            if await table_exists(cur, "message_feedback"):
                print("  [跳过] message_feedback 表已存在")
            else:
                await cur.execute(CREATE_FEEDBACK)
                print("  [完成] 创建 message_feedback 表")

            # 3. handoff_tickets 表
            if await table_exists(cur, "handoff_tickets"):
                print("  [跳过] handoff_tickets 表已存在")
            else:
                await cur.execute(CREATE_HANDOFF)
                print("  [完成] 创建 handoff_tickets 表")

        print("\n迁移完成！")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
