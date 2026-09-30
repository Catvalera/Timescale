"""Тесты работают с отдельной БД PostgreSQL.

Перед запуском создайте её:  createdb -U postgres timescale_db_test
Строку подключения можно переопределить переменной TEST_DATABASE_URL.
"""
import asyncio
import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/timescale_db_test"
)

from datetime import datetime, timedelta, timezone  # noqa: E402

import jwt  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

from app import models  # noqa: E402,F401
from app.config import settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.main import app  # noqa: E402


async def _recreate_schema() -> None:
    engine = create_async_engine(os.environ["DATABASE_URL"])
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def make_token(token_type: str = "access", secret: str | None = None, exp_delta: int = 3600) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode({"sub": "1", "type": token_type, "iss": "auth-service", "email": "t@example.com",
                       "nickname": "tester", "iat": now, "exp": now + timedelta(seconds=exp_delta)},
                      secret or settings.secret_key, algorithm="HS256")


@pytest.fixture(scope="session")
def anon_client():
    asyncio.run(_recreate_schema())
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def client(anon_client):
    anon_client.headers[settings.access_header_token_name] = make_token()
    return anon_client


@pytest.fixture(autouse=True)
def clean_tables(client):
    client.delete("/api/Table_actions/clear_table_Value")
    client.delete("/api/Table_actions/clear_table_Result")
    yield


def upload(client, name: str, content: str):
    return client.post("/Upload_file", files={"file": (name, content.encode("utf-8"), "text/csv")})
