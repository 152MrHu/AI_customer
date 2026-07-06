"""Knowledge Service - FastAPI 应用入口

知识库管理微服务，端口 8003。
负责知识库 CRUD、文档上传/解析/切块/向量化入库。
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.response import success_response
from common.database import create_pool, close_pool
from common.http_client import create_client, close_client
from common.logging_config import setup_logger, get_logger
from common.exception_handlers import register_exception_handlers

from .routers import knowledge_base, document, vector_search

setup_logger()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化 MySQL 连接池、httpx 客户端、上传目录"""
    logger.info("Knowledge Service 启动中...")

    # 初始化 MySQL 连接池
    await create_pool()
    logger.info("MySQL 连接池已初始化")

    # 初始化 httpx 异步客户端
    await create_client()
    logger.info("httpx 客户端已初始化")

    # 确保上传目录存在
    upload_dir = settings.upload_dir_path
    logger.info("上传目录: %s", upload_dir)

    # 自动重试所有 pending/failed 文档
    from .services.ingest_service import schedule_ingest
    from common.database import DB
    try:
        async with DB() as db:
            stuck_docs = await db.fetchall(
                "SELECT document_id FROM documents WHERE status IN ('pending', 'failed')"
            )
        if stuck_docs:
            logger.info("发现 %d 条 pending/failed 文档，自动重试入库", len(stuck_docs))
            for doc in stuck_docs:
                schedule_ingest(doc["document_id"])
        else:
            logger.info("无 pending/failed 文档需要重试")
    except Exception as e:
        logger.warning("自动重试入库失败: %s", e)

    logger.info("Knowledge Service 启动完成，监听端口 8003")
    yield

    # 清理资源
    await close_client()
    await close_pool()
    logger.info("Knowledge Service 已关闭")


app = FastAPI(title="Knowledge Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 健康检查
@app.get("/health")
async def health():
    """Knowledge Service 健康检查"""
    return success_response({"status": "healthy", "service": "knowledge_service"})

# 注册全局异常处理器
register_exception_handlers(app)

# 挂载路由
app.include_router(knowledge_base.router)
app.include_router(document.router)
app.include_router(vector_search.router)


if __name__ == "__main__":
    uvicorn.run(
        "knowledge_service.main:app",
        host="127.0.0.1",
        port=8003,
        reload=True,
    )
