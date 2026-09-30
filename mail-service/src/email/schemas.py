from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class VerifyCode(BaseModel):
    email: EmailStr
    code: str = Field(..., pattern=r"^\d{6}$", description="Verification code")
    purpose: Literal["registration", "login"] = Field(..., description="What the code confirms")
    name: str | None = Field(None, description="Full name of user")
    expires_minutes: int = Field(10, ge=1, le=1440)


class SuccessRegistration(BaseModel):
    email: EmailStr
    name: str
    nickname: str


class SuccessLogin(BaseModel):
    email: EmailStr
    name: str
    logged_in_at: datetime
    ip: str | None = None
    user_agent: str | None = None
