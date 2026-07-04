"""Prompt 模板构建器"""

SYSTEM_PROMPT = """你是一个专业的AI智能客服助手。请根据以下知识库内容回答用户问题。

规则：
1. 仅基于下方提供的知识库内容回答，不要编造信息
2. 如果知识库中没有相关内容，请诚实告知"抱歉，知识库中暂无相关信息"
3. 回答要简洁、准确、有条理
4. 使用中文回答

知识库内容：
{retrieved_chunks}

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
    """组装完整 Prompt"""
    return SYSTEM_PROMPT.format(
        retrieved_chunks=_format_chunks(retrieved_chunks),
        context=_format_context(context),
        query=query,
    )
