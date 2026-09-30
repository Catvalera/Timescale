from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.database import DatabaseMethods
from src.core.errors import ServiceError
from src.users.models import User, Verify


class UserCore(DatabaseMethods):
    model = User

    @classmethod
    async def find_by_email(cls, email: str, session: AsyncSession) -> User | None:
        # verify подгружается сразу: в async-сессии ленивая загрузка связей невозможна
        return await session.scalar(
            select(User).options(selectinload(User.verify)).where(User.email == email.lower()))

    @classmethod
    async def get_with_verify(cls, id: int, session: AsyncSession) -> User:
        user = await session.scalar(select(User).options(selectinload(User.verify)).where(User.id == id))
        if user is None:
            raise ServiceError.NotFoundObject(log=f"User with id={id} not found!")
        return user

    @classmethod
    async def find_by_nickname(cls, nickname: str, session: AsyncSession) -> User | None:
        return await session.scalar(select(User).where(func.lower(User.nickname) == nickname.lower()))


class VerifyCore(DatabaseMethods):
    model = Verify
