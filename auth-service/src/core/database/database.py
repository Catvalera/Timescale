from typing import Any, ClassVar, Generic, TypeVar

from sqlalchemy import MetaData, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlmodel import SQLModel

from src.core.config import settings
from src.core.errors.exceptions import ServiceError

metadata = MetaData(schema=settings.DB_SCHEMA)


SYNC_DATABASE_URL = (
    f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)
ASYNC_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.DB_USER}:{settings.DB_PASSWORD}"
    f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

engine = create_async_engine(ASYNC_DATABASE_URL, echo=settings.DB_ECHO)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


class Base(SQLModel):
    metadata = metadata


async def get_async_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session


ModelType = TypeVar("ModelType", bound=Base)


class DatabaseMethods(Generic[ModelType]):
    model: ClassVar[type[ModelType]]

    @classmethod
    async def get_object(cls, id: int, session: AsyncSession) -> ModelType:
        instance = await session.get(cls.model, id)
        if instance is None:
            raise ServiceError.NotFoundObject(log=f"{cls.model.__name__} with id={id} not found!")
        return instance

    @classmethod
    async def get_object_by(cls, session: AsyncSession, **kwargs: Any) -> ModelType:
        instance = await session.scalar(select(cls.model).filter_by(**kwargs))
        if not instance:
            raise ServiceError.NotFoundObject(log=f"{cls.model.__name__} not found!")
        return instance

    @classmethod
    async def find_object_by(cls, session: AsyncSession, **kwargs: Any) -> ModelType | None:
        return await session.scalar(select(cls.model).filter_by(**kwargs))

    @classmethod
    async def create_object(cls, session: AsyncSession, **kwargs: Any) -> ModelType:
        instance: ModelType = cls.model(**kwargs)
        session.add(instance)
        return instance
