"""LLM 适配器工厂"""
from common.config import settings
from common.logging_config import get_logger
from .base import LLMAdapter
from .dashscope_adapter import DashScopeAdapter

logger = get_logger()


def create_adapter(config=settings) -> LLMAdapter:
    """根据配置创建 LLM 适配器实例"""
    provider = getattr(config, "LLM_PROVIDER", "dashscope").lower()

    if provider == "dashscope":
        logger.info("创建 DashScope 适配器, llm=%s, embedding=%s",
                    config.LLM_MODEL, config.EMBEDDING_MODEL)
        return DashScopeAdapter(
            api_key=config.DASHSCOPE_API_KEY,
            llm_model=config.LLM_MODEL,
            embedding_model=config.EMBEDDING_MODEL,
        )

    # TODO: 预留 OpenAI 适配分支
    # if provider == "openai":
    #     from .openai_adapter import OpenAIAdapter
    #     return OpenAIAdapter(
    #         api_key=config.OPENAI_API_KEY,
    #         llm_model=config.LLM_MODEL,
    #         embedding_model=config.EMBEDDING_MODEL,
    #     )

    logger.warning("未知的 LLM 提供商: %s, 回退到 DashScope", provider)
    return DashScopeAdapter(
        api_key=config.DASHSCOPE_API_KEY,
        llm_model=config.LLM_MODEL,
        embedding_model=config.EMBEDDING_MODEL,
    )
