import logging
from enum import StrEnum
from typing import Any

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors
from pydantic import EmailStr

from src.core.config import settings
from src.core.errors import ServiceError

logger = logging.getLogger(__name__)


def build_connection_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.EMAIL_HOST_USER,
        MAIL_PASSWORD=settings.EMAIL_PASSWORD,
        MAIL_FROM=settings.EMAIL_HOST_USER,
        MAIL_FROM_NAME=settings.EMAIL_FROM_NAME,
        MAIL_PORT=settings.EMAIL_PORT,
        MAIL_SERVER=settings.EMAIL_HOST,
        MAIL_STARTTLS=settings.EMAIL_STARTTLS,
        MAIL_SSL_TLS=settings.EMAIL_SSL_TLS,
        USE_CREDENTIALS=settings.EMAIL_USE_CREDENTIALS,
        VALIDATE_CERTS=settings.EMAIL_STARTTLS or settings.EMAIL_SSL_TLS,
        TIMEOUT=settings.EMAIL_TIMEOUT,
        TEMPLATE_FOLDER=settings.TEMPLATES_PATH,
    )


class Templates(StrEnum):
    VERIFICATION = "verification.html"
    SUCCESS_REGISTRATION = "success-registration.html"
    SUCCESS_LOGIN = "success-login.html"


class MailService:
    fm = FastMail(build_connection_config())

    @classmethod
    def build(
        cls,
        subject: str,
        recipients: list[EmailStr],
        template_data: dict[str, Any],
    ) -> MessageSchema:
        return MessageSchema(
            subject=subject,
            recipients=recipients,
            template_body={
                "app_name": settings.APP_NAME,
                "logo_url": settings.LOGO_URL,
                "app_url": settings.APP_URL,
                **template_data,
            },
            subtype=MessageType.html,
        )

    @classmethod
    async def send(
        cls,
        subject: str,
        recipients: list[EmailStr],
        template_name: Templates,
        template_data: dict[str, Any] | None = None,
    ) -> dict:
        message = cls.build(subject, recipients, template_data or {})
        try:
            await cls.fm.send_message(message, template_name=template_name.value)
        except ConnectionErrors as error:
            logger.error("SMTP error while sending «%s» to %s: %s", subject, recipients, error)
            raise ServiceError.SmtpUnavailable(log=f"SMTP server is unavailable: {error}") from error
        logger.info("Mail «%s» sent to %s", subject, recipients)
        return {"message": "Mail sent"}
