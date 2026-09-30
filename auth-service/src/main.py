import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.auth.router import router as auth_router
from src.core.config import settings
from src.core.database import engine
from src.core.errors.handlers import register_exception_handlers
from src.core.http import HttpService
from src.core.results import ResultData, ResultStatus
from src.users.router import router as users_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await HttpService.startup()
    try:
        yield
    finally:
        await HttpService.shutdown()
        await engine.dispose()


app = FastAPI(
    title="Timescale Auth Server",
    description="Регистрация и вход по почте и паролю с подтверждением кодом, JWT-токены",
    version="0.0.1",
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

register_exception_handlers(app)


@app.get("/api/healthy", tags=["root"])
async def hello():
    return ResultData(status=ResultStatus.success, data=[{"message": "Welcome to the Timescale Auth Server"}])


auth_app = APIRouter(prefix="/api")
auth_app.include_router(auth_router)
auth_app.include_router(users_router, prefix="/user")

app.include_router(auth_app)
