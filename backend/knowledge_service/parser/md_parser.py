"""Markdown 文件解析"""


async def parse_md(file_path: str) -> str:
    """解析 Markdown 文件，兼容 UTF-8 和 GBK 编码"""
    for encoding in ("utf-8", "gbk"):
        try:
            with open(file_path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    # 两种编码都失败，用 UTF-8 忽略错误字符
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()
