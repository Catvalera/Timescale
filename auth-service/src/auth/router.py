from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.schemas import UserBase, UserLogin, VerificationCodeBase
from src.auth.service import AuthService
from src.core.database.database import get_async_session
from src.core.results import ResultData, standard_response
from src.core.security.TokenService import TokenService

router = APIRouter(tags=["Authorization"])


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.headers.get("x-real-ip") or (request.client.host if request.client else None)


@router.post("/registration", response_model=ResultData)
@standard_response
async def registration(
    user_data: UserBase,
    session: AsyncSession = Depends(get_async_session),
):
    """Регистрация: создаёт неподтверждённого пользователя и отправляет код на почту.
    Возвращает verify-токен (в поле token.access_token)."""
    return await AuthService.register_user(user_data, session)


@router.post("/login", response_model=ResultData)
@standard_response
async def login(
    user: UserLogin,
    session: AsyncSession = Depends(get_async_session),
):
    """Вход по почте и паролю: отправляет код на почту и возвращает verify-токен.
    Если почта ещё не подтверждена, отправляется код регистрации (data.purpose = registration)."""
    return await AuthService.login_user(user, session)


@router.post("/verify", response_model=ResultData)
@standard_response
async def verify(
    verify_data: VerificationCodeBase,
    request: Request,
    background_tasks: BackgroundTasks,
    token_data: dict = Depends(TokenService.get_verify_data),
    session: AsyncSession = Depends(get_async_session),
):
    """Подтверждение кода из письма (verify-токен в заголовке X-Access-Token). Возвращает пару токенов."""
    return await AuthService.verify_user(verify_data, token_data, session, background_tasks,
                                         _client_ip(request), request.headers.get("user-agent"))


@router.post("/verify/resend", response_model=ResultData)
@standard_response
async def resend_code(
    token_data: dict = Depends(TokenService.get_verify_data),
    session: AsyncSession = Depends(get_async_session),
):
    """Повторная отправка кода (не чаще, чем раз в CODE_RESEND_SECONDS)."""
    return await AuthService.resend_code(token_data, session)


@router.post("/logout", response_model=ResultData)
@standard_response
async def logout(_: int = Depends(TokenService.get_current_user_id)):
    return AuthService.logout_user()


@router.post("/tokens/refresh", response_model=ResultData)
@standard_response
async def refresh_tokens(
    user_id: int = Depends(TokenService.get_refresh_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    """Новая пара токенов по refresh-токену (заголовок X-Refresh-Token)."""
    return await AuthService.refresh_tokens(user_id, session)
