"""PDF 文件解析（PyMuPDF）"""
import fitz  # PyMuPDF


async def parse_pdf(file_path: str) -> str:
    """用 PyMuPDF 提取 PDF 文本"""
    doc = fitz.open(file_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text
