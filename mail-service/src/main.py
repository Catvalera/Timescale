import logging

from fastapi import APIRouter, FastAPI

from src.core.errors.handlers import register_exception_handlers
from src.core.results import ResultData, ResultStatus
from src.email.router import router as email_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="Timescale Mail Service",
    description="Отправка кодов подтверждения и уведомлений о регистрации/входе",
    version="0.0.1",
)

register_exception_handlers(app)


@app.get("/api/healthy", tags=["root"])
async def hello():
    return ResultData(status=ResultStatus.success, data=[{"message": "Welcome to the Timescale Mail Service"}])


mail_app = APIRouter(prefix="/api")
mail_app.include_router(email_router, prefix="/send")

app.include_router(mail_app)
