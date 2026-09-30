"""Проверка access-токена из заголовка X-Access-Token (имя задаётся ACCESS_HEADER_TOKEN_NAME).

Токены выпускает auth-service; здесь проверяются подпись, срок действия, издатель и тип.
В базу сервиса авторизации этот сервис не ходит.
"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import settings

access_header = APIKeyHeader(name=settings.access_header_token_name, scheme_name="AccessToken", auto_error=False,
                             description="Access-токен, полученный в auth-service")


@dataclass(frozen=True)
class CurrentUser:
    id: int
    email: str
    nickname: str


def _unauthorized(detail: str = "Требуется авторизация") -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail)


async def get_current_user(token: str | None = Depends(access_header)) -> CurrentUser:
    if not token:
        raise _unauthorized()
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm_encryption],
                             issuer=settings.token_issuer, options={"require": ["exp", "sub", "iss"]})
    except jwt.ExpiredSignatureError:
        raise _unauthorized("Срок действия токена истёк") from None
    except jwt.PyJWTError:
        raise _unauthorized("Недействительный токен") from None
    if payload.get("type") != "access":
        raise _unauthorized("Неверный тип токена")
    return CurrentUser(id=int(payload["sub"]), email=payload.get("email", ""), nickname=payload.get("nickname", ""))
