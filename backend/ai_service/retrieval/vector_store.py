"""远程向量检索封装 - 通过 knowledge_service API 查询向量存储

避免多进程同时访问 SQLite 导致的文件锁 hang 死问题。
只有 knowledge_service 直接操作 SQLite，ai_service 通过 HTTP 调用检索。
"""
from typing import Optional

import httpx

from common.config import settings
from common.http_client import get_client
from common.logging_config import get_logger

logger = get_logger()

# knowledge_service 向量检索地址
_SEARCH_URL = f"{settings.KNOWLEDGE_SERVICE_URL}/api/knowledge/search"
_COUNT_URL = f"{settings.KNOWLEDGE_SERVICE_URL}/api/knowledge/count"


class VectorStoreError(Exception):
    """向量检索服务不可用时抛出的异常"""
    pass


class VectorStore:
    """远程向量检索（通过 knowledge_service API）"""

    async def query(
        self, kb_id: int, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        """
        远程向量检索：
        调用 knowledge_service /api/knowledge/search，
        返回 [{"doc_name", "score", "snippet", "document"}]
        如果 knowledge_service 不可达则抛出 VectorStoreError
        """
        client = get_client()
        try:
            resp = await client.post(
                _SEARCH_URL,
                json={
                    "kb_id": kb_id,
                    "query_embedding": query_embedding,
                    "top_k": top_k,
                },
                timeout=httpx.Timeout(10.0, connect=5.0),
            )
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", [])
            # 业务错误（非 200），记录并返回空
            logger.warning("远程检索业务错误 kb_id=%s, code=%s", kb_id, data.get("code"))
            return []
        except httpx.TimeoutException:
            logger.error("远程检索超时 kb_id=%s", kb_id)
            raise VectorStoreError("知识库检索服务超时，请稍后重试")
        except httpx.ConnectError:
            logger.error("远程检索连接失败 kb_id=%s (knowledge_service 不可达)", kb_id)
            raise VectorStoreError("知识库服务暂时不可用，请联系管理员")
        except Exception as e:
            logger.error("远程检索失败 kb_id=%s: %s", kb_id, e)
            raise VectorStoreError(f"知识库检索异常: {str(e)}")

    async def count_collection(self, kb_id: int) -> int:
        """远程查询 collection 中向量数量，失败时抛出 VectorStoreError"""
        client = get_client()
        try:
            resp = await client.post(
                _COUNT_URL,
                json={"kb_id": kb_id},
                timeout=httpx.Timeout(5.0, connect=3.0),
            )
            data = resp.json()
            if data.get("code") == 200:
                return data.get("data", {}).get("count", 0)
            logger.warning("远程计数业务错误 kb_id=%s, code=%s", kb_id, data.get("code"))
            return 0
        except httpx.TimeoutException:
            logger.error("远程计数超时 kb_id=%s", kb_id)
            raise VectorStoreError("知识库计数服务超时，请稍后重试")
        except httpx.ConnectError:
            logger.error("远程计数连接失败 kb_id=%s (knowledge_service 不可达)", kb_id)
            raise VectorStoreError("知识库服务暂时不可用，请联系管理员")
        except Exception as e:
            logger.error("远程计数失败 kb_id=%s: %s", kb_id, e)
            raise VectorStoreError(f"知识库计数异常: {str(e)}")
