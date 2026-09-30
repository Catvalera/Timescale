"""Регистрация и вход с подтверждением кодом из письма.

Регистрация:  POST /registration  → письмо с кодом + verify-токен
              POST /verify         → почта подтверждена, пара токенов, письмо «регистрация завершена»
Вход:         POST /login          → проверка почты и пароля, письмо с кодом + verify-токен
              POST /verify         → пара токенов, письмо «выполнен вход»
"""
import logging

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from src.auth.results import AuthResult, TokenPair
from src.auth.schemas import UserBase, UserLogin, VerificationCodeBase
from src.core.config import settings
from src.core.email import EmailService
from src.core.errors import ServiceError
from src.core.security import TokenService
from src.users.core import UserCore
from src.users.models import User, Verify, utcnow

logger = logging.getLogger(__name__)

REGISTRATION = "registration"
LOGIN = "login"

# Хеш-заглушка: проверяется, если пользователя нет, чтобы время ответа не выдавало существование почты
_DUMMY_HASH = User.hash_password("dummy-password-for-timing")


class AuthService:

    @staticmethod
    async def register_user(data: UserBase, session: AsyncSession) -> AuthResult:
        password_hash = await run_in_threadpool(User.hash_password, data.password)
        async with session.begin():
            user = await UserCore.find_by_email(data.email, session)
            if user is not None and user.is_verified:
                raise ServiceError.ObjectAlreadyExist()

            nick_owner = await UserCore.find_by_nickname(data.nickname, session)
            if nick_owner is not None and (user is None or nick_owner.id != user.id):
                raise ServiceError.NicknameAlreadyExist()

            if user is None:
                user = await UserCore.create_object(session=session, email=data.email, is_verified=False,
                                                    full_name=data.full_name, nickname=data.nickname,
                                                    password=password_hash)
                user.verify = Verify()
            else:
                # Регистрация начата, но почта не подтверждена: обновляем данные и отправляем новый код
                AuthService._check_resend(user.verify)
                user.full_name, user.nickname, user.password = data.full_name, data.nickname, password_hash
            await session.flush()

            # Письмо отправляется внутри транзакции: если почта недоступна, пользователь не сохранится
            await AuthService._send_code(user, REGISTRATION)
        return AuthService._verification_result(user, REGISTRATION)

    @staticmethod
    async def login_user(data: UserLogin, session: AsyncSession) -> AuthResult:
        async with session.begin():
            user = await UserCore.find_by_email(data.email, session)
            ok = await run_in_threadpool(User.verify_password, data.password, user.password if user else _DUMMY_HASH)
            if user is None or not ok:
                raise ServiceError.InvalidCredentials()

            # Почта не подтверждена — вместо входа завершаем регистрацию
            purpose = LOGIN if user.is_verified else REGISTRATION
            verify = AuthService._get_verify(user)
            # Если код для этой же цели только что отправлен — не шлём повторно, он уже в почте
            if not (verify.is_active(purpose) and verify.seconds_until_resend() > 0):
                await AuthService._send_code(user, purpose)
        return AuthService._verification_result(user, purpose)

    @staticmethod
    async def verify_user(data: VerificationCodeBase, token_data: dict, session: AsyncSession,
                          background_tasks: BackgroundTasks, ip: str | None, user_agent: str | None) -> AuthResult:
        purpose: str = token_data["purpose"]
        async with session.begin():
            user: User = await UserCore.get_with_verify(int(token_data["sub"]), session)
            verify = AuthService._get_verify(user)

            if not verify.is_active(purpose):
                raise ServiceError.VerificationCodeExpired()
            if verify.attempts >= settings.CODE_MAX_ATTEMPTS:
                raise ServiceError.TooManyAttempts()

            if not verify.check_code(data.code):
                verify.attempts += 1
                left = settings.CODE_MAX_ATTEMPTS - verify.attempts
                error = ServiceError.InvalidVerificationCode(log=f"Неверный код. Осталось попыток: {left}")
            else:
                error = None
                verify.clear_code()
                user.last_login_at = utcnow()
                if purpose == REGISTRATION:
                    user.is_verified = True
        # Выход из блока фиксирует транзакцию: счётчик попыток сохраняется и при неверном коде
        if error is not None:
            raise error

        if purpose == REGISTRATION:
            logger.info("Пользователь %s подтвердил регистрацию", user.email)
            background_tasks.add_task(EmailService.send_successful_registration,
                                      user.email, user.full_name, user.nickname)
        else:
            logger.info("Пользователь %s вошёл в систему", user.email)
            background_tasks.add_task(EmailService.send_successful_login,
                                      user.email, user.full_name, user.last_login_at, ip, user_agent)
        return AuthService._authorize(user)

    @staticmethod
    async def resend_code(token_data: dict, session: AsyncSession) -> AuthResult:
        purpose: str = token_data["purpose"]
        async with session.begin():
            user: User = await UserCore.get_with_verify(int(token_data["sub"]), session)
            if purpose == REGISTRATION and user.is_verified:
                raise ServiceError.InvalidToken(log="Почта уже подтверждена")
            verify = AuthService._get_verify(user)
            AuthService._check_resend(verify)
            await AuthService._send_code(user, purpose)
        return AuthService._verification_result(user, purpose)

    @staticmethod
    async def refresh_tokens(user_id: int, session: AsyncSession) -> TokenPair:
        async with session.begin():
            user: User | None = await session.get(User, user_id)
            if user is None or not user.is_verified:
                raise ServiceError.InvalidToken()
        return TokenPair(*TokenService.create_pair_token(user.token_claims()))

    @staticmethod
    def logout_user() -> TokenPair:
        return TokenPair.empty()

    # ---------- вспомогательное ----------
    @staticmethod
    def _get_verify(user: User) -> Verify:
        if user.verify is None:
            user.verify = Verify(id=user.id)
        return user.verify

    @staticmethod
    def _check_resend(verify: Verify | None) -> None:
        if verify is not None and verify.code:
            wait = verify.seconds_until_resend()
            if wait > 0:
                raise ServiceError.VerificationCodeAlreadySent(
                    log=f"Код уже отправлен на почту. Повторно запросить его можно через {wait} с")

    @staticmethod
    async def _send_code(user: User, purpose: str) -> None:
        code = AuthService._get_verify(user).create_code(purpose)
        await EmailService.send_verification_code(user.email, code, purpose, user.full_name)

    @staticmethod
    def _verification_result(user: User, purpose: str) -> AuthResult:
        return AuthResult(
            access_token=TokenService.create_verify_token(user.id, purpose),
            need_verify=True,
            data={
                "purpose": purpose,
                "email": user.email,
                "resend_after": user.verify.seconds_until_resend() if user.verify else 0,
                "expires_in": settings.CODE_EXPIRE_SECONDS,
            },
        )

    @staticmethod
    def _authorize(user: User) -> AuthResult:
        access, refresh = TokenService.create_pair_token(user.token_claims())
        return AuthResult(access_token=access, refresh_token=refresh, data={"user": user.serialize()})
