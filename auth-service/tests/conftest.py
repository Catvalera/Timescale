"""Тестам нужна отдельная БД (пересоздаётся при запуске):  createdb -U postgres auth_service_test"""
import asyncio
import os

os.environ.setdefault("DB_NAME", "auth_service_test")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

import src.models  # noqa: E402,F401
from src.core.config import settings  # noqa: E402
from src.core.database.database import ASYNC_DATABASE_URL, Base  # noqa: E402
from src.core.email import EmailService  # noqa: E402
from src.core.errors import ServiceError  # noqa: E402
from src.main import app  # noqa: E402

ACCESS = settings.ACCESS_HEADER_TOKEN_NAME
REFRESH = settings.REFRESH_HEADER_TOKEN_NAME


async def _run(sql: str | None = None):
    engine = create_async_engine(ASYNC_DATABASE_URL)
    async with engine.begin() as conn:
        if sql is None:
            await conn.execute(text(f'DROP SCHEMA IF EXISTS "{settings.DB_SCHEMA}" CASCADE'))
            await conn.execute(text(f'CREATE SCHEMA "{settings.DB_SCHEMA}"'))
            await conn.run_sync(Base.metadata.create_all)
        else:
            await conn.execute(text(sql))
    await engine.dispose()


def run_sql(sql: str) -> None:
    asyncio.run(_run(sql))


@pytest.fixture(scope="session")
def client():
    asyncio.run(_run())
    with TestClient(app) as c:
        yield c


class MailBox:
    """Заглушка mail-service: запоминает отправленные письма."""

    def __init__(self):
        self.sent: list[tuple[str, dict]] = []
        self.down = False

    async def post(self, url: str, payload: dict) -> None:
        if self.down:
            raise ServiceError.MailServiceUnavailable()
        self.sent.append((url, payload))

    def last_code(self, email: str) -> str:
        for url, p in reversed(self.sent):
            if url == "send/verify-code" and p["email"] == email:
                return p["code"]
        raise AssertionError("code not sent")

    def urls(self) -> list[str]:
        return [u for u, _ in self.sent]


@pytest.fixture
def mailbox(monkeypatch, client):
    box = MailBox()
    monkeypatch.setattr(EmailService, "_post", staticmethod(box.post))
    run_sql(f'TRUNCATE "{settings.DB_SCHEMA}".users RESTART IDENTITY CASCADE')
    return box
