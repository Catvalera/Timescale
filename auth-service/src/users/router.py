from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database.database import get_async_session
from src.core.results import ResultData, standard_response
from src.core.security import TokenService
from src.users.service import UserService

router = APIRouter(tags=["User"])


@router.get("/get-data", response_model=ResultData)
@standard_response
async def get_data_user(
    user_id: int = Depends(TokenService.get_current_user_id),
    session: AsyncSession = Depends(get_async_session),
):
    """Данные текущего пользователя (без хеша пароля)."""
    return await UserService.get_user(user_id, session)
