"""全局异常处理器注册"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from common.exceptions import BusinessError
from common.response import error_response, ErrorCode
from common.logging_config import get_logger

logger = get_logger()


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        return JSONResponse(
            status_code=200,
            content=error_response(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        # 只返回验证错误数量，不泄露字段细节
        error_count = len(exc.errors())
        return JSONResponse(
            status_code=422,
            content=error_response(
                ErrorCode.PARAM_ERROR,
                f"请求参数校验失败（{error_count} 项）",
            ),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        # 记录完整异常便于排查，但只返回通用错误消息
        logger.error(
            "未处理异常: path=%s method=%s error=%s",
            request.url.path if hasattr(request, 'url') else '?',
            request.method if hasattr(request, 'method') else '?',
            exc,
            exc_info=True,
        )
        return JSONResponse(
            status_code=500,
            content=error_response(ErrorCode.SERVER_ERROR, "服务器内部错误，请稍后重试"),
        )
