"""AI Service - FastAPI 应用入口

提供 RAG 流式问答、文本向量化等能力，端口 8004。
ChromaDB 操作已改为通过 knowledge_service 远程调用，
本服务不再直接访问 ChromaDB（避免多进程文件锁冲突）。
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.logging_config import setup_logger, get_logger
from common.exception_handlers import register_exception_handlers
from common.http_client import create_client, close_client

from .adapter.factory import create_adapter
from .dependencies import set_adapter
from .routers import chat, embedding, health

setup_logger()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化 LLM 适配器（ChromaDB 通过远程调用，不再本地初始化）"""
    logger.info("AI Service 启动中...")

    # 初始化 httpx 客户端（用于调用 knowledge_service 检索接口）
    await create_client()
    logger.info("httpx 客户端已初始化")

    # 初始化 LLM 适配器
    adapter = create_adapter(settings)
    set_adapter(adapter)
    logger.info("LLM 适配器已初始化: %s / %s",
                settings.LLM_MODEL, settings.EMBEDDING_MODEL)

    logger.info("AI Service 启动完成，监听端口 8004")
    yield

    await close_client()
    logger.info("AI Service 关闭")


app = FastAPI(title="AI Service", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册全局异常处理器
register_exception_handlers(app)

# 挂载路由
app.include_router(health.router)
app.include_router(embedding.router)
app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run(
        "ai_service.main:app",
        host="127.0.0.1",
        port=8004,
        reload=True,
    )
