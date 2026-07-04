"""API Gateway - 网关服务入口

统一入口，负责请求转发、JWT 鉴权、限流、日志，端口 8000。
中间件层次（外 -> 内）：CORS -> RequestLog -> JWTAuth -> RateLimit -> 路由
"""
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from common.config import settings
from common.redis_client import create_redis, close_redis
from common.http_client import create_client, close_client
from common.logging_config import setup_logger

from gateway.middleware import (
    RequestLogMiddleware,
    JWTAuthMiddleware,
    RateLimitMiddleware,
)
from gateway.proxy import router as proxy_router

logger = setup_logger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化 Redis、httpx 客户端"""
    logger.info("API Gateway 启动中...")
    await create_redis()
    await create_client()
    logger.info("API Gateway 启动完成，监听端口 8000")
    yield
    logger.info("API Gateway 关闭中...")
    await close_client()
    await close_redis()
    logger.info("API Gateway 已关闭")


app = FastAPI(title="API Gateway", lifespan=lifespan)

# 注册中间件（Starlette 中 add_middleware 后注册的位于更外层）
# 期望层次：CORS(最外) -> RequestLog -> JWTAuth -> RateLimit(最内) -> 路由
# 所以按 内层 -> 外层 的顺序调用 add_middleware
app.add_middleware(RateLimitMiddleware)
app.add_middleware(JWTAuthMiddleware)
app.add_middleware(RequestLogMiddleware)

# CORS（最后添加 = 最外层，处理预检请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# 挂载通配代理路由
app.include_router(proxy_router)


if __name__ == "__main__":
    uvicorn.run(
        "gateway.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
