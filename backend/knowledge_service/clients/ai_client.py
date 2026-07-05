"""AI Service 客户端 - 调用 ai-service 的向量化接口"""
import httpx

from common.config import settings


async def get_embeddings(texts: list[str], kb_id: int) -> list[list[float]]:
    """调用 ai-service /api/ai/embedding 批量向量化（带独立超时保护）

    使用独立的 httpx 客户端和较短超时，避免占用全局客户端连接。
    """
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(60.0, connect=10.0),
        limits=httpx.Limits(max_keepalive_connections=0),
    )
    try:
        resp = await client.post(
            f"{settings.AI_SERVICE_URL}/api/ai/embedding",
            json={"texts": texts, "kb_id": kb_id},
        )
        data = resp.json()
        if data.get("code") != 200:
            raise Exception(f"Embedding failed: {data.get('message')}")
        return data["data"]["embeddings"]
    finally:
        await client.aclose()
