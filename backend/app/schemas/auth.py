"""认证相关 Schema。"""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fa5]{2,32}$")


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=64)

    @field_validator("username")
    @classmethod
    def _check_username(cls, v: str) -> str:
        if not USERNAME_RE.match(v):
            raise ValueError("用户名只能包含字母、数字、下划线或中文，长度 2-32")
        return v


class LoginRequest(BaseModel):
    account: str = Field(..., description="用户名或邮箱")
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    is_active: bool = True


class UpdateProfileRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=32)
    password: Optional[str] = Field(None, min_length=6, max_length=64)
