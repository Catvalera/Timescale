import re

from pydantic import EmailStr, field_validator
from sqlmodel import Field, SQLModel

NICKNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")


class UserBase(SQLModel):
    full_name: str = Field(..., min_length=2, max_length=200, description="ФИО",
                           schema_extra={"examples": ["Иванов Иван Иванович"]})
    email: EmailStr = Field(..., description="Email address")
    nickname: str = Field(..., description="Никнейм: 3–32 символа, латиница, цифры, «_», «.», «-»",
                          schema_extra={"examples": ["ivanov"]})
    password: str = Field(..., description="Пароль: от 8 символов, буквы и цифры",
                          schema_extra={"examples": ["Secret123"]})

    @field_validator("full_name")
    @classmethod
    def _full_name(cls, v: str) -> str:
        v = " ".join(v.split())
        if len(v) < 2:
            raise ValueError("ФИО слишком короткое")
        return v

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("nickname")
    @classmethod
    def _nickname(cls, v: str) -> str:
        v = v.strip()
        if not NICKNAME_RE.fullmatch(v):
            raise ValueError("никнейм: 3–32 символа, латиница, цифры, «_», «.», «-»")
        return v

    @field_validator("password")
    @classmethod
    def _password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("пароль должен быть не короче 8 символов")
        if len(v) > 128:
            raise ValueError("пароль слишком длинный (максимум 128 символов)")
        if not re.search(r"[A-Za-zА-Яа-яЁё]", v) or not re.search(r"\d", v):
            raise ValueError("пароль должен содержать буквы и цифры")
        return v


class UserLogin(SQLModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., min_length=1, max_length=128, description="Password")

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return v.strip().lower()


class VerificationCodeBase(SQLModel):
    code: str = Field(..., min_length=6, max_length=6, regex=r"^\d{6}$", description="Verification code")
