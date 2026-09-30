from zoneinfo import ZoneInfo

from fastapi import APIRouter

from src.core.results import ResultData, standard_response
from src.email.schemas import SuccessLogin, SuccessRegistration, VerifyCode
from src.email.service import MailService, Templates

router = APIRouter(tags=["Send"])

MSK = ZoneInfo("Europe/Moscow")

SUBJECTS = {
    "registration": "Код подтверждения регистрации",
    "login": "Код для входа в аккаунт",
}


@router.post("/verify-code", response_model=ResultData)
@standard_response
async def send_verification_code(data: VerifyCode):
    """Код подтверждения: при регистрации и при входе."""
    return await MailService.send(
        subject=f"{SUBJECTS[data.purpose]}: {data.code}",
        recipients=[data.email],
        template_name=Templates.VERIFICATION,
        template_data=data.model_dump(),
    )


@router.post("/success-registration", response_model=ResultData)
@standard_response
async def send_success_registration(data: SuccessRegistration):
    """Уведомление об успешной регистрации."""
    return await MailService.send(
        subject="Регистрация завершена",
        recipients=[data.email],
        template_name=Templates.SUCCESS_REGISTRATION,
        template_data=data.model_dump(),
    )


@router.post("/success-login", response_model=ResultData)
@standard_response
async def send_success_login(data: SuccessLogin):
    """Уведомление об успешном входе."""
    return await MailService.send(
        subject="Выполнен вход в аккаунт",
        recipients=[data.email],
        template_name=Templates.SUCCESS_LOGIN,
        template_data={
            **data.model_dump(),
            "logged_in_at": data.logged_in_at.astimezone(MSK).strftime("%d.%m.%Y %H:%M (МСК)"),
        },
    )
