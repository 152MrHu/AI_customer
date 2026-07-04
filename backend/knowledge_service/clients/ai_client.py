"""AI Service 客户端 - 调用 ai-service 的向量化接口"""
from common.config import settings
from common.http_client import post_json


async def get_embeddings(texts: list[str], kb_id: int) -> list[list[float]]:
    """调用 ai-service /api/ai/embedding 批量向量化"""
    resp = await post_json(
        f"{settings.AI_SERVICE_URL}/api/ai/embedding",
        json={"texts": texts, "kb_id": kb_id},
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Embedding failed: {data.get('message')}")
    return data["data"]["embeddings"]
