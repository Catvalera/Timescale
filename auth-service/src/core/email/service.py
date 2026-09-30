"""Клиент почтового микросервиса (mail-service)."""
import logging
from datetime import datetime

import httpx
from pydantic import EmailStr

from src.core.config import settings
from src.core.errors import ServiceError
from src.core.http import HttpService

logger = logging.getLogger(__name__)


class EmailService:

    @staticmethod
    async def _post(url: str, payload: dict) -> None:
        try:
            resp = await HttpService.get_mail_client().post(url=url, json=payload)
            resp.raise_for_status()
        except httpx.HTTPError as error:
            logger.error("mail-service: %s -> %s", url, error)
            raise ServiceError.MailServiceUnavailable() from error

    @staticmethod
    async def send_verification_code(email: EmailStr, code: str, purpose: str, name: str) -> None:
        """Код нужен пользователю сразу, поэтому отправка синхронная: при ошибке регистрация/вход откатываются."""
        await EmailService._post("send/verify-code", {
            "email": email, "code": code, "purpose": purpose, "name": name,
            "expires_minutes": settings.CODE_EXPIRE_SECONDS // 60,
        })

    @staticmethod
    async def send_successful_registration(email: EmailStr, name: str, nickname: str) -> None:
        """Уведомление отправляется в фоне (BackgroundTasks): сбой почты не ломает регистрацию."""
        try:
            await EmailService._post("send/success-registration", {"email": email, "name": name, "nickname": nickname})
        except ServiceError.MailServiceUnavailable:
            pass

    @staticmethod
    async def send_successful_login(email: EmailStr, name: str, logged_in_at: datetime,
                                    ip: str | None, user_agent: str | None) -> None:
        try:
            await EmailService._post("send/success-login", {
                "email": email, "name": name, "logged_in_at": logged_in_at.isoformat(),
                "ip": ip, "user_agent": (user_agent or "")[:300] or None,
            })
        except ServiceError.MailServiceUnavailable:
            pass
