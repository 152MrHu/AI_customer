"""文本清洗与切块"""
import re


def clean_text(text: str) -> str:
    """文本清洗：统一换行符，去多余空白"""
    if not text:
        return ""
    # 统一换行符
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # 合并连续空格/制表符
    text = re.sub(r"[ \t]+", " ", text)
    # 三个以上连续换行压缩为两个
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> list[str]:
    """文本切块：
    - 按 chunk_size 切分
    - 每块之间有 overlap 重叠
    - 尽量在句号或段落边界切分
    """
    text = clean_text(text)
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    # 句子/段落边界字符
    boundary_chars = set("。.！!？?；;\n")

    while start < len(text):
        end = min(start + chunk_size, len(text))

        # 已到文本末尾，取剩余部分
        if end >= len(text):
            chunk = text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break

        # 在 chunk 末尾的 overlap 范围内寻找句子边界
        search_start = max(start + 1, end - overlap)
        boundary = end
        for i in range(end - 1, search_start - 1, -1):
            if text[i] in boundary_chars:
                boundary = i + 1
                break

        chunk = text[start:boundary].strip()
        if chunk:
            chunks.append(chunk)

        # 下一切块起点：回退 overlap 长度，保证重叠
        next_start = boundary - overlap
        if next_start <= start:
            next_start = start + 1  # 确保前进
        start = next_start

    return chunks
