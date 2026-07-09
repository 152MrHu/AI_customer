"""文件上传路由 - 提取文字内容作为对话上下文"""
import os
import uuid
import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File
from common.dependencies import get_current_user
from common.config import settings
from common.response import success_response, ErrorCode
from common.exceptions import BusinessError
from common.logging_config import get_logger

logger = get_logger()

router = APIRouter(prefix="/api/chat", tags=["文件上传"])

# 图片格式
IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
# 文档格式
DOC_EXTENSIONS = {"txt", "pdf", "docx", "md", "csv"}
# 限制
MAX_IMAGE_SIZE = 10 * 1024 * 1024   # 10MB
MAX_DOC_SIZE = 20 * 1024 * 1024     # 20MB


async def _extract_image_text(file_path: str) -> str:
    """通过 DashScope 多模态模型提取图片文字（OCR）"""
    import dashscope
    from dashscope import MultiModalConversation

    # 尝试调用 DashScope qwen-vl-ocr
    def _call():
        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"file://{file_path}"},
                    {"text": "请提取并输出这张图片中的所有文字内容，保持原有格式和排版。只输出文字，不要添加任何解释。"},
                ],
            }
        ]
        response = MultiModalConversation.call(
            model="qwen-vl-ocr",
            messages=messages,
            api_key=settings.DASHSCOPE_API_KEY,
        )
        return response

    try:
        response = await asyncio.to_thread(_call)
        output = getattr(response, "output", None)
        if output and "choices" in output:
            choices = output["choices"]
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "")
                if isinstance(content, list):
                    return "".join(
                        item.get("text", "") for item in content if isinstance(item, dict)
                    )
                return str(content) if content else ""
        return ""
    except Exception as e:
        logger.warning("DashScope OCR 失败, 回退到空文本: %s", e)
        return ""


async def _parse_document(file_path: str, ext: str) -> str:
    """复用 knowledge_service 解析器提取文档文字"""
    try:
        if ext == "txt" or ext == "md":
            from knowledge_service.parser.text_parser import parse_text
            return await parse_text(file_path)
        elif ext == "pdf":
            from knowledge_service.parser.pdf_parser import parse_pdf
            return await parse_pdf(file_path)
        elif ext == "docx":
            from knowledge_service.parser.docx_parser import parse_docx
            return await parse_docx(file_path)
        elif ext == "csv":
            from knowledge_service.parser.csv_parser import parse_csv
            return await parse_csv(file_path)
        else:
            raise ValueError(f"不支持的文件类型: {ext}")
    except ImportError as e:
        logger.error("导入解析器失败: %s", e)
        raise BusinessError(ErrorCode.SERVER_ERROR, "文件解析服务不可用")
    except Exception as e:
        logger.error("文件解析失败: %s", e)
        raise BusinessError(ErrorCode.PARAM_ERROR, f"文件解析失败: {str(e)}")


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    """上传文件或图片，提取文字内容作为对话上下文。
    图片 → OCR 文字提取，文档 → 解析文本内容。
    """
    raw_name = file.filename or "unknown"
    ext = raw_name.rsplit(".", 1)[-1].lower() if "." in raw_name else ""
    is_image = ext in IMAGE_EXTENSIONS
    is_doc = ext in DOC_EXTENSIONS

    if not is_image and not is_doc:
        raise BusinessError(
            ErrorCode.PARAM_ERROR,
            f"不支持的文件格式 .{ext}，图片支持: {', '.join(IMAGE_EXTENSIONS)}，文档支持: {', '.join(DOC_EXTENSIONS)}",
        )

    max_size = MAX_IMAGE_SIZE if is_image else MAX_DOC_SIZE
    content = await file.read()
    file_size = len(content)
    if file_size > max_size:
        limit_mb = max_size // (1024 * 1024)
        raise BusinessError(ErrorCode.FILE_TOO_LARGE, f"文件大小不能超过 {limit_mb}MB")

    # 保存临时文件
    upload_dir = Path(settings.UPLOAD_DIR) / "chat_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{uuid.uuid4().hex}_{raw_name}"
    file_path = upload_dir / safe_name
    file_path.write_bytes(content)

    try:
        if is_image:
            text = await _extract_image_text(str(file_path))
            if not text:
                raise BusinessError(ErrorCode.PARAM_ERROR, "未能从图片中提取文字，请确保图片包含清晰文字")
        else:
            text = await _parse_document(str(file_path), ext)

        if not text or not text.strip():
            raise BusinessError(ErrorCode.PARAM_ERROR, "文件中未提取到文字内容")

        # 截断过长文本
        max_chars = 10000
        if len(text) > max_chars:
            text = text[:max_chars] + "\n...(内容过长已截断)"

        return success_response({
            "text": text,
            "file_name": raw_name,
            "file_type": ext,
            "char_count": len(text),
        })
    finally:
        # 清理临时文件
        try:
            file_path.unlink(missing_ok=True)
        except Exception:
            pass
