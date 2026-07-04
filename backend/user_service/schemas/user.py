"""用户服务 Pydantic 模型"""
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ========== 请求模型 ==========

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=20, description="用户名(3-20字符)")
    phone: str = Field(..., description="手机号(11位)")
    email: Optional[str] = Field(None, description="邮箱(可选)")
    password: str = Field(..., description="密码(至少8位，含字母和数字)")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[A-Za-z0-9_]{3,20}$", v):
            raise ValueError("用户名只能包含字母、数字、下划线，长度3-20")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not re.match(r"^1[3-9]\d{9}$", v):
            raise ValueError("手机号格式不正确，需为11位")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not re.match(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", v):
            raise ValueError("邮箱格式不正确")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("密码至少8位")
        if not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            raise ValueError("密码必须同时包含字母和数字")
        return v


class LoginRequest(BaseModel):
    account: str = Field(..., min_length=1, description="用户名或手机号")
    password: str = Field(..., min_length=1, description="密码")
    remember_me: bool = Field(False, description="记住我(7天有效期)")


class UpdateStatusRequest(BaseModel):
    status: int = Field(..., description="状态：0-禁用 1-启用")

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: int) -> int:
        if v not in (0, 1):
            raise ValueError("status 只能为 0 或 1")
        return v


# ========== 响应模型 ==========

class UserResponse(BaseModel):
    user_id: int
    username: str
    phone: str
    email: Optional[str] = None
    role: str
    status: int
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None


class UserListItem(BaseModel):
    user_id: int
    username: str
    phone: str
    email: Optional[str] = None
    role: str
    status: int
    created_at: Optional[str] = None


class RegisterResponse(BaseModel):
    user_id: int
    username: str


class LoginUserInfo(BaseModel):
    user_id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    token: str
    expires_in: int
    user: LoginUserInfo
