import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import ClassVar, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from pydantic import EmailStr
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, String
from sqlmodel import Field, Relationship

from src.core.config import settings
from src.core.database.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base, table=True):
    __tablename__ = "users"

    password_hasher: ClassVar[PasswordHasher] = PasswordHasher()   # argon2id

    id: int | None = Field(default=None, sa_type=BigInteger, primary_key=True)
    full_name: str = Field(sa_type=String(200), nullable=False)
    email: EmailStr = Field(sa_type=String(320), unique=True, index=True, nullable=False)  # в нижнем регистре
    nickname: str = Field(sa_type=String(32), unique=True, index=True, nullable=False)
    password: str = Field(nullable=False)                                          # хеш argon2, не пароль
    is_verified: bool = Field(default=False, nullable=False)
    created_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True), nullable=False)
    last_login_at: datetime | None = Field(default=None, sa_type=DateTime(timezone=True))

    verify: Optional["Verify"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan", "uselist": False})

    @classmethod
    def hash_password(cls, password: str) -> str:
        return cls.password_hasher.hash(password)

    @classmethod
    def verify_password(cls, plain_password: str, hashed_password: str) -> bool:
        try:
            return cls.password_hasher.verify(hashed_password, plain_password)
        except (VerificationError, InvalidHashError):
            return False

    def token_claims(self) -> dict:
        return {"sub": str(self.id), "email": self.email, "nickname": self.nickname, "name": self.full_name}

    def serialize(self) -> dict:
        return self.model_dump(exclude={"password"})


class Verify(Base, table=True):
    """Текущий код подтверждения пользователя (одна строка на пользователя, как в исходном проекте).

    Сам код не хранится — только его HMAC-SHA256.
    """
    __tablename__ = "verify"

    id: int = Field(sa_column=Column(BigInteger, ForeignKey(f"{settings.DB_SCHEMA}.users.id", ondelete="CASCADE"),
                                     primary_key=True))
    purpose: str = Field(default="", sa_type=String(16), nullable=False)       # registration | login
    code: str = Field(default="", sa_type=String(64), nullable=False)          # HMAC кода
    attempts: int = Field(default=0, nullable=False)
    sent_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True), nullable=False)
    expires_at: datetime = Field(default_factory=utcnow, sa_type=DateTime(timezone=True), nullable=False)

    user: Optional[User] = Relationship(back_populates="verify")

    @staticmethod
    def _hash(code: str) -> str:
        return hmac.new(settings.SECRET_KEY.encode(), code.encode(), hashlib.sha256).hexdigest()

    def create_code(self, purpose: str) -> str:
        """Генерирует новый код, сбрасывает попытки и возвращает код в открытом виде (для письма)."""
        code = f"{secrets.randbelow(10 ** 6):06d}"
        now = utcnow()
        self.purpose = purpose
        self.code = self._hash(code)
        self.attempts = 0
        self.sent_at = now
        self.expires_at = now + timedelta(seconds=settings.CODE_EXPIRE_SECONDS)
        return code

    def clear_code(self) -> None:
        self.code = ""
        self.purpose = ""
        self.attempts = 0
        self.expires_at = utcnow()

    def is_active(self, purpose: str) -> bool:
        return bool(self.code) and self.purpose == purpose and self.expires_at > utcnow()

    def seconds_until_resend(self) -> int:
        return max(0, settings.CODE_RESEND_SECONDS - int((utcnow() - self.sent_at).total_seconds()))

    def check_code(self, code: str) -> bool:
        return bool(self.code) and hmac.compare_digest(self._hash(code), self.code)
