"""JWT-токены. Передаются в заголовках (имена задаются в .env):

  X-Access-Token  — access-токен (type=access) или временный verify-токен (type=verify)
  X-Refresh-Token — refresh-токен (type=refresh)

verify-токен выдаётся после ввода почты и пароля (или регистрации) и позволяет
только подтвердить код из письма. К остальному API с ним доступа нет.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt
from fastapi import Depends
from fastapi.security import APIKeyHeader

from src.core.config import settings
from src.core.errors.exceptions import ServiceError

TokenType = Literal["access", "refresh", "verify"]
VerifyPurpose = Literal["registration", "login"]


class TokenService:
    access_header = APIKeyHeader(
        name=settings.ACCESS_HEADER_TOKEN_NAME,
        scheme_name="AccessToken",
        auto_error=False,
    )
    refresh_header = APIKeyHeader(
        name=settings.REFRESH_HEADER_TOKEN_NAME,
        scheme_name="RefreshToken",
        auto_error=False,
    )

    @classmethod
    def _encode(cls, data: dict, token_type: TokenType, lifetime_seconds: int) -> str:
        now = datetime.now(timezone.utc)
        payload = data | {
            "type": token_type,
            "iss": settings.TOKEN_ISSUER,
            "iat": now,
            "exp": now + timedelta(seconds=lifetime_seconds),
            "jti": uuid.uuid4().hex,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM_ENCRYPTION)

    @classmethod
    def create_pair_token(cls, data: dict) -> tuple[str, str]:
        """data — claims access-токена (sub, email, nickname, name). В refresh кладётся только sub."""
        return (
            cls._encode(data, "access", settings.ACCESS_TOKEN_EXPIRE_SECONDS),
            cls._encode({"sub": data["sub"]}, "refresh", settings.REFRESH_TOKEN_EXPIRE_SECONDS),
        )

    @classmethod
    def create_verify_token(cls, user_id: int, purpose: VerifyPurpose) -> str:
        return cls._encode({"sub": str(user_id), "purpose": purpose}, "verify", settings.VERIFY_TOKEN_EXPIRE_SECONDS)

    @classmethod
    def decode_token(cls, token: str, expected_type: TokenType) -> dict:
        try:
            data = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM_ENCRYPTION],
                issuer=settings.TOKEN_ISSUER, options={"require": ["exp", "iat", "sub", "iss"]},
            )
        except jwt.ExpiredSignatureError:
            raise ServiceError.InvalidToken(log="Срок действия токена истёк") from None
        except jwt.PyJWTError:
            raise ServiceError.InvalidToken() from None
        if data.get("type") != expected_type:
            raise ServiceError.InvalidToken(log="Неверный тип токена")
        return data

    # ---------- зависимости FastAPI ----------
    @classmethod
    def get_current_user_id(cls, token: str | None = Depends(access_header)) -> int:
        if not token:
            raise ServiceError.Unauthorized()
        return int(cls.decode_token(token, "access")["sub"])

    @classmethod
    def get_verify_data(cls, token: str | None = Depends(access_header)) -> dict:
        if not token:
            raise ServiceError.Unauthorized()
        return cls.decode_token(token, "verify")

    @classmethod
    def get_refresh_user_id(cls, token: str | None = Depends(refresh_header)) -> int:
        if not token:
            raise ServiceError.Unauthorized()
        return int(cls.decode_token(token, "refresh")["sub"])
