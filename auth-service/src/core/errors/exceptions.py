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

    # --- 400 Bad Request ---
    class InvalidCredentials(ServiceException):
        http_status_code = 400
        code = 100
        log = "Неверная почта или пароль"

    class InvalidVerificationCode(ServiceException):
        http_status_code = 400
        code = 101
        log = "Неверный код"

    class VerificationCodeExpired(ServiceException):
        http_status_code = 400
        code = 108
        log = "Код недействителен или истёк. Запросите новый код"

    # --- 401 Unauthorized ---
    class Unauthorized(ServiceException):
        http_status_code = 401
        code = 102
        log = "Требуется авторизация"

    class InvalidToken(ServiceException):
        http_status_code = 401
        code = 103
        log = "Недействительный токен"

    # --- 403 Forbidden ---
    class Forbidden(ServiceException):
        http_status_code = 403
        code = 104
        log = "Доступ запрещён"

    # --- 404 Not Found ---
    class NotFoundObject(ServiceException):
        http_status_code = 404
        code = 105
        log = "Объект не найден"

    # --- 409 Conflict ---
    class ObjectAlreadyExist(ServiceException):
        http_status_code = 409
        code = 106
        log = "Пользователь с такой почтой уже зарегистрирован"

    class NicknameAlreadyExist(ServiceException):
        http_status_code = 409
        code = 109
        log = "Никнейм уже занят"

    # --- 429 Too Many Requests ---
    class VerificationCodeAlreadySent(ServiceException):
        http_status_code = 429
        code = 107
        log = "Код уже отправлен на почту. Повторно запросить его можно чуть позже"

    class TooManyAttempts(ServiceException):
        http_status_code = 429
        code = 110
        log = "Слишком много неверных попыток. Запросите новый код"

    # --- 503 Service Unavailable ---
    class MailServiceUnavailable(ServiceException):
        http_status_code = 503
        code = 111
        log = "Не удалось отправить письмо. Попробуйте позже"
