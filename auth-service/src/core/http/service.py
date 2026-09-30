import httpx

from src.core.config import settings


class HttpService:
    """Общий HTTP-клиент для обращений к другим микросервисам. Создаётся и закрывается в lifespan."""

    mail_client: httpx.AsyncClient | None = None

    @classmethod
    async def startup(cls) -> None:
        cls.mail_client = httpx.AsyncClient(base_url=settings.MAIL_SERVICE, timeout=settings.MAIL_TIMEOUT_SECONDS)

    @classmethod
    async def shutdown(cls) -> None:
        if cls.mail_client is not None:
            await cls.mail_client.aclose()
            cls.mail_client = None

    @classmethod
    def get_mail_client(cls) -> httpx.AsyncClient:
        if cls.mail_client is None:
            raise RuntimeError("HTTP-клиент не инициализирован (проверьте lifespan)")
        return cls.mail_client
