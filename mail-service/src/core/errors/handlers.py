import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from src.core.errors.exceptions import ServiceException
from src.core.results import ErrorData, ResultData, ResultStatus

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(ServiceException)
    async def service_exception_handler(request: Request, exc: ServiceException) -> JSONResponse:
        result = ResultData(status=ResultStatus.error, error=exc.error)
        return JSONResponse(status_code=exc.http_status_code, content=result.model_dump())

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        result = ResultData(status=ResultStatus.error, error=ErrorData(code=422, log=str(exc.errors())))
        return JSONResponse(status_code=422, content=result.model_dump())

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled error")
        result = ResultData(status=ResultStatus.error, error=ErrorData(code=500, log="Internal server error"))
        return JSONResponse(status_code=500, content=result.model_dump())
