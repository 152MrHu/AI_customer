"""JWT 签发与校验"""
import uuid
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional
from common.config import settings


def create_token(user_id: int, username: str, role: str, remember_me: bool = False) -> str:
    """签发 JWT Token（含 jti 唯一标识用于撤销追踪）"""
    hours = settings.JWT_REMEMBER_HOURS if remember_me else settings.JWT_EXPIRE_HOURS
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user_id,
        "username": username,
        "role": role,
        "jti": uuid.uuid4().hex,  # 每个 token 唯一标识
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """解码 JWT Token，失败返回 None"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_token_ttl_seconds() -> int:
    """获取 Token 有效期（秒）"""
    return settings.JWT_EXPIRE_HOURS * 3600
