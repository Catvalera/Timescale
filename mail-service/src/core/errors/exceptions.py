from src.core.results import ErrorData


class ServiceException(Exception):
    http_status_code: int
    code: int
    log: str

    def __init__(self, log: str | None = None) -> None:
        self.log = log or self.log
        super().__init__(self.log)

    @property
    def error(self) -> ErrorData:
        return ErrorData(code=self.code, log=self.log)


class ServiceError:

    # --- 502 Bad Gateway ---
    class SmtpUnavailable(ServiceException):
        http_status_code = 502
        code = 200
        log = "SMTP server is unavailable"
