"""Точка входа (аналог Program.cs).

Запуск:  uvicorn app.main:app --reload --port 5145
Swagger: http://localhost:5145/swagger  (кнопка Authorize — вставить access-токен из auth-service)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.auth import get_current_user
from app.config import settings
from app.database import engine
from app.routers import filter_data, last_ten_values, table_actions, upload_and_read

logging.basicConfig(level=settings.log_level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="TimescaleApi", version="v1", docs_url="/swagger", redoc_url=None, lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

# Все эндпоинты данных доступны только авторизованным пользователям
protected = [Depends(get_current_user)]
app.include_router(filter_data.router, dependencies=protected)
app.include_router(last_ten_values.router, dependencies=protected)
app.include_router(table_actions.router, dependencies=protected)
app.include_router(upload_and_read.router, dependencies=protected)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/swagger")


@app.get("/health", tags=["service"])
async def health():
    return {"status": "ok"}
