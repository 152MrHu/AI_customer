"""DOCX 文件解析（python-docx）"""
from docx import Document


async def parse_docx(file_path: str) -> str:
    """用 python-docx 提取 Word 文本"""
    doc = Document(file_path)
    return "\n".join([para.text for para in doc.paragraphs if para.text.strip()])
