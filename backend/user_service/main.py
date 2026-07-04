"""User Service - 用户服务入口"""
import uvicorn
from contextlib import asynccontextmanager

from fastapi import FastAPI

from common.database import create_pool, close_pool
from common.redis_client import create_redis, close_redis
from common.exception_handlers import register_exception_handlers
from common.logging_config import setup_logger

from user_service.routers.user import router

logger = setup_logger("user_service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化资源，关闭时释放"""
    logger.info("User Service 启动中...")
    await create_pool()
    await create_redis()
    logger.info("User Service 启动完成，监听端口 8001")
    yield
    logger.info("User Service 关闭中...")
    await close_redis()
    await close_pool()
    logger.info("User Service 已关闭")


app = FastAPI(title="User Service", lifespan=lifespan)

# 注册全局异常处理器
register_exception_handlers(app)

# 挂载路由
app.include_router(router)


if __name__ == "__main__":
    uvicorn.run(
        "user_service.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
    )
