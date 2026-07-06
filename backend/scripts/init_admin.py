"""初始化管理员账户和默认知识库 - 生成真实 bcrypt hash"""
import asyncio
import sys
from pathlib import Path

import aiomysql

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config import settings
from common.security import hash_password


async def init_admin():
    print("正在初始化管理员账户和默认知识库...")

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
            # 检查管理员是否已存在
            await cur.execute("SELECT user_id FROM users WHERE username = 'admin'")
            if await cur.fetchone():
                print("管理员账户已存在，跳过创建。")
            else:
                password_hash = hash_password("admin123")
                await cur.execute(
                    "INSERT INTO users (username, phone, email, password_hash, role, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    ("admin", "13800000000", "admin@example.com", password_hash, "admin", 1),
                )
                print("  管理员账户创建成功: admin / admin123 (role=admin)")

            # 创建默认知识库
            await cur.execute("SELECT kb_id FROM knowledge_bases WHERE name = '默认知识库'")
            if await cur.fetchone():
                print("默认知识库已存在，跳过创建。")
            else:
                await cur.execute(
                    "INSERT INTO knowledge_bases (name, description, document_count) "
                    "VALUES (%s, %s, %s)",
                    ("默认知识库", "系统默认主知识库，未指定知识库的会话默认使用", 0),
                )
                print("  默认知识库创建成功")

            # 创建测试用户
            await cur.execute("SELECT user_id FROM users WHERE username = 'testuser'")
            if await cur.fetchone():
                print("测试用户已存在，跳过创建。")
            else:
                password_hash = hash_password("user123")
                await cur.execute(
                    "INSERT INTO users (username, phone, email, password_hash, role, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    ("testuser", "13800138000", "test@example.com", password_hash, "user", 1),
                )
                print("  测试用户创建成功: testuser / user123 (role=user)")

            # 创建默认客服账户
            await cur.execute("SELECT user_id FROM users WHERE username = 'agent1'")
            if await cur.fetchone():
                print("默认客服已存在，跳过创建。")
            else:
                password_hash = hash_password("agent123")
                await cur.execute(
                    "INSERT INTO users (username, phone, email, password_hash, role, status) "
                    "VALUES (%s, %s, %s, %s, %s, %s)",
                    ("agent1", "13900000001", "agent1@example.com", password_hash, "agent", 1),
                )
                print("  默认客服创建成功: agent1 / agent123 (role=agent)")

        print("\n初始化完成！")
        print("可用账户:")
        print("  管理员: admin / admin123")
        print("  测试用户: testuser / user123")
        print("  客服:    agent1 / agent123")
    finally:
        conn.close()


if __name__ == "__main__":
    asyncio.run(init_admin())
