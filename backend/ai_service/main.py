"""AI Service - FastAPI 应用入口

提供 RAG 流式问答、文本向量化等能力，端口 8004。
"""
from contextlib import asynccontextmanager

import chromadb
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.logging_config import setup_logger, get_logger
from common.exception_handlers import register_exception_handlers

from .adapter.factory import create_adapter
from .dependencies import set_adapter, set_chroma_client
from .routers import chat, embedding, health

setup_logger()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化 ChromaDB 客户端与 LLM 适配器"""
    logger.info("AI Service 启动中...")

    # 初始化 ChromaDB PersistentClient
    chroma_client = chromadb.PersistentClient(path=settings.chroma_path)
    set_chroma_client(chroma_client)
    logger.info("ChromaDB 已初始化, path=%s", settings.chroma_path)

    # 初始化 LLM 适配器
    adapter = create_adapter(settings)
    set_adapter(adapter)
    logger.info("LLM 适配器已初始化: %s / %s",
                settings.LLM_MODEL, settings.EMBEDDING_MODEL)

    logger.info("AI Service 启动完成，监听端口 8004")
    yield

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
        host="0.0.0.0",
        port=8004,
        reload=True,
    )
