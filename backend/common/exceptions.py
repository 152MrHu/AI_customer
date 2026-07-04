"""自定义业务异常"""
from typing import Any, Optional


class BusinessError(Exception):
    """业务异常，携带错误码和消息"""

    def __init__(self, code: int, message: str, data: Any = None):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(message)


# 便捷构造函数
def param_error(msg: str = "参数错误") -> BusinessError:
    return BusinessError(1001, msg)


def not_found(msg: str = "资源不存在") -> BusinessError:
    return BusinessError(1002, msg)


def unauthorized(msg: str = "未授权") -> BusinessError:
    return BusinessError(401, msg)


def forbidden(msg: str = "禁止访问") -> BusinessError:
    return BusinessError(403, msg)
