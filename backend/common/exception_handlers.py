"""全局异常处理器注册"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from common.exceptions import BusinessError
from common.response import error_response, ErrorCode


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        return JSONResponse(
            status_code=200,
            content=error_response(exc.code, exc.message, exc.data),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=200,
            content=error_response(ErrorCode.PARAM_ERROR, f"参数错误: {exc.errors()}"),
        )

    @app.exception_handler(Exception)
    async def general_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=200,
            content=error_response(ErrorCode.SERVER_ERROR, f"服务器内部错误: {str(exc)}"),
        )
