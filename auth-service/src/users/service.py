from sqlalchemy.ext.asyncio import AsyncSession

from src.users.core import UserCore
from src.users.models import User


class UserService:
    @staticmethod
    async def get_user(id: int, session: AsyncSession) -> dict:
        async with session.begin():
            user: User = await UserCore.get_object(id=id, session=session)
            return user.serialize()
