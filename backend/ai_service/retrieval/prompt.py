"""Prompt 模板构建器"""

SYSTEM_PROMPT_RAG = """你是一个专业的AI智能客服助手。请根据以下知识库内容回答用户问题。

规则：
1. 优先基于下方提供的知识库内容回答，不要编造信息
2. 如果知识库中没有相关内容，请结合你的通用知识友好回答
3. 回答要简洁、准确、有条理
4. 使用中文回答

知识库内容：
{retrieved_chunks}

对话历史：
{context}

用户问题：{query}"""

# 知识库为空时的通用助手模式
SYSTEM_PROMPT_GENERAL = """你是一个友好的AI智能客服助手。

规则：
1. 友好、专业地回答用户的问题
2. 回答要简洁、准确、有条理
3. 使用中文回答
4. 如果用户问的是产品/业务相关问题且知识库暂无内容，可以告知"目前知识库中还没有相关资料，建议您联系人工客服获取更准确的信息"

对话历史：
{context}

用户问题：{query}"""


def _format_chunks(retrieved_chunks: list[dict]) -> str:
    """将检索片段格式化为文本"""
    if not retrieved_chunks:
        return "（暂无相关内容）"

    lines = []
    for idx, chunk in enumerate(retrieved_chunks, start=1):
        doc_name = chunk.get("doc_name", "未知文档")
        document = chunk.get("document") or chunk.get("snippet", "")
        score = chunk.get("score", 0.0)
        lines.append(f"[{idx}] 来源：{doc_name}（相似度：{score}）\n{document}")
    return "\n\n".join(lines)


def _format_context(context: list[dict]) -> str:
    """将对话历史格式化为文本"""
    if not context:
        return "（无历史对话）"

    lines = []
    for msg in context:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        role_label = "用户" if role == "user" else "客服"
        lines.append(f"{role_label}：{content}")
    return "\n".join(lines)


def build_prompt(retrieved_chunks: list[dict], context: list[dict], query: str) -> str:
    """组装完整 Prompt。知识库为空时使用通用助手模式，否则使用 RAG 模式。"""
    if retrieved_chunks:
        # RAG 模式：有检索结果
        return SYSTEM_PROMPT_RAG.format(
            retrieved_chunks=_format_chunks(retrieved_chunks),
            context=_format_context(context),
            query=query,
        )
    else:
        # 通用助手模式：知识库为空或无检索结果
        return SYSTEM_PROMPT_GENERAL.format(
            context=_format_context(context),
            query=query,
        )
