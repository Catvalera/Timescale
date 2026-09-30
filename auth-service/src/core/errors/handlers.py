import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.errors.exceptions import ServiceException
from src.core.results import ErrorData, ResultData, ResultStatus

logger = logging.getLogger(__name__)


def _validation_log(exc: RequestValidationError) -> str:
    """Человекочитаемый текст ошибок валидации: «поле: причина»."""
    parts = []
    for err in exc.errors():
        field = ".".join(str(p) for p in err.get("loc", ())[1:]) or "body"
        message = str(err.get("msg", "")).removeprefix("Value error, ")
        parts.append(f"{field}: {message}")
    return "; ".join(parts)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
        result = ResultData(status=ResultStatus.error, error=exc.error)
        return JSONResponse(status_code=exc.http_status_code, content=result.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        result = ResultData(status=ResultStatus.error, error=ErrorData(code=422, log=_validation_log(exc)))
        return JSONResponse(status_code=422, content=result.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        result = ResultData(status=ResultStatus.error, error=ErrorData(code=500, log="Внутренняя ошибка сервера"))
        return JSONResponse(status_code=500, content=result.model_dump())
