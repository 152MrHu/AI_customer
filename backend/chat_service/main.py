"""Chat Service - 对话服务入口

提供会话管理与 SSE 流式问答，端口 8002。
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from common.database import create_pool, close_pool
from common.response import success_response
from common.redis_client import create_redis, close_redis
from common.http_client import create_client, close_client
from common.exception_handlers import register_exception_handlers
from common.logging_config import setup_logger

from chat_service.routers.session import router

logger = setup_logger("chat_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化资源，关闭时释放"""
    logger.info("Chat Service 启动中...")
    await create_pool()
    await create_redis()
    await create_client()
    logger.info("Chat Service 启动完成，监听端口 8002")
    yield
    logger.info("Chat Service 关闭中...")
    await close_client()
    await close_redis()
    await close_pool()
    logger.info("Chat Service 已关闭")


app = FastAPI(title="Chat Service", lifespan=lifespan)

# 健康检查
@app.get("/health")
async def health():
    """Chat Service 健康检查"""
    return success_response({"status": "healthy", "service": "chat_service"})

# 注册全局异常处理器
register_exception_handlers(app)

# 挂载路由
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "chat_service.main:app",
        host="127.0.0.1",
        port=8002,
        reload=True,
    )
