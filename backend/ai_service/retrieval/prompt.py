"""Prompt 模板构建器 - 支持双模式"""

# ===== 知识库模式（严格 RAG） =====
SYSTEM_PROMPT_KB = """你是一个专业的AI智能客服助手。请严格根据以下知识库内容回答用户问题。

规则：
1. 仅基于下方提供的知识库内容回答，不得编造或猜测任何信息
2. 如果知识库中没有与用户问题相关的内容，请明确回答"抱歉，知识库中暂无相关信息，无法回答您的问题"
3. 回答要简洁、准确、有条理
4. 使用中文回答

知识库内容：
{retrieved_chunks}

对话历史：
{context}

用户问题：{query}"""

# ===== 通用助手模式（LLM + 搜索增强） =====
SYSTEM_PROMPT_ASSISTANT = """你是一个友好、智能的AI客服助手，可以联网搜索获取信息来回答用户问题。

规则：
1. 根据搜索结果和你的知识，准确、全面地回答用户问题
2. 如果搜索到了相关信息，请引用来源并整理后给出回答
3. 如果没有搜索到相关信息，请基于自身知识尽量回答，并告知"以上信息未经过联网验证，建议您联系人工客服获取更准确的信息"
4. 回答要简洁、准确、有条理
5. 使用中文回答

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


def build_prompt(retrieved_chunks: list[dict], context: list[dict], query: str, mode: str = "kb") -> str:
    """组装完整 Prompt，根据模式选择模板。"""
    if mode == "assistant":
        # 通用助手模式：不包含知识库内容
        return SYSTEM_PROMPT_ASSISTANT.format(
            context=_format_context(context),
            query=query,
        )
    else:
        # 知识库模式：严格基于知识库内容
        return SYSTEM_PROMPT_KB.format(
            retrieved_chunks=_format_chunks(retrieved_chunks),
            context=_format_context(context),
            query=query,
        )
