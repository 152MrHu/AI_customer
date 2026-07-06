"""Redis 客户端 - redis.asyncio 异步"""
import redis.asyncio as aioredis
from typing import Optional
from common.config import settings

_redis: Optional[aioredis.Redis] = None


async def create_redis():
    """创建 Redis 客户端，应用启动时调用"""
    global _redis
    _redis = aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        password=settings.REDIS_PASSWORD or None,
        db=0,
        decode_responses=True,
    )
    await _redis.ping()
    return _redis


async def close_redis():
    """关闭 Redis 连接"""
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


def get_redis() -> aioredis.Redis:
    if _redis is None:
        raise RuntimeError("Redis 未初始化，请先调用 create_redis()")
    return _redis


# ========== Token 黑名单 ==========
async def blacklist_token(token: str, ttl_seconds: int):
    """将 Token 加入黑名单"""
    r = get_redis()
    await r.setex(f"blacklist:{token}", ttl_seconds, "1")


async def is_blacklisted(token: str) -> bool:
    """检查 Token 是否在黑名单中"""
    r = get_redis()
    return await r.exists(f"blacklist:{token}") > 0


# ========== 登录失败计数 ==========
async def incr_login_fail(identifier: str | int) -> int:
    """递增登录失败次数（按 user_id 或账号），返回当前次数"""
    r = get_redis()
    key = f"login_fail:{identifier}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 1800)  # 30 分钟
    return count


async def get_login_fail_count(identifier: str | int) -> int:
    """获取登录失败次数"""
    r = get_redis()
    val = await r.get(f"login_fail:{identifier}")
    return int(val) if val else 0


async def clear_login_fail(identifier: str | int):
    """清除登录失败计数"""
    r = get_redis()
    await r.delete(f"login_fail:{identifier}")


# ========== 限流计数 ==========
async def incr_rate_limit(user_id: int) -> int:
    """递增限流计数"""
    r = get_redis()
    key = f"rate_limit:{user_id}"
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, 60)  # 1 分钟
    return count


async def get_rate_limit_count(user_id: int) -> int:
    """获取限流计数"""
    r = get_redis()
    val = await r.get(f"rate_limit:{user_id}")
    return int(val) if val else 0


# ========== 通用计数器（自定义 TTL） ==========
async def incr_with_ttl(key: str, ttl_seconds: int) -> int:
    """递增一个带 TTL 的计数器，返回当前值"""
    r = get_redis()
    count = await r.incr(key)
    if count == 1:
        await r.expire(key, ttl_seconds)
    return count


async def get_count(key: str) -> int:
    """获取计数器当前值"""
    r = get_redis()
    val = await r.get(key)
    return int(val) if val else 0


# ========== 会话缓存 ==========
async def cache_session(session_id: int, data: dict, ttl: int = 7200):
    """缓存会话信息"""
    r = get_redis()
    await r.hset(f"session:{session_id}", mapping=data)
    await r.expire(f"session:{session_id}", ttl)


async def get_cached_session(session_id: int) -> Optional[dict]:
    """获取缓存的会话信息"""
    r = get_redis()
    data = await r.hgetall(f"session:{session_id}")
    return data if data else None


async def delete_cached_session(session_id: int):
    """删除会话缓存"""
    r = get_redis()
    await r.delete(f"session:{session_id}")
