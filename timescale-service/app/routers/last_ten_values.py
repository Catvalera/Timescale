"""Аналог Controllers/Last_ten_valuesController.cs."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ResultEntry
from app.schemas import ResultEntryOut

router = APIRouter(tags=["Last_ten_values"])


@router.get("/Get_last_10_values_filter_from_filename", response_model=list[ResultEntryOut])
async def get_value(Full_filename: str, session: AsyncSession = Depends(get_session)):
    # 10 последних добавленных записей, чьё имя файла содержит строку, затем сортировка по дате старта.
    stmt = (select(ResultEntry)
            .where(ResultEntry.file_name.contains(Full_filename, autoescape=True))
            .order_by(ResultEntry.id.desc())
            .limit(10))
    rows = (await session.scalars(stmt)).all()
    return sorted(rows, key=lambda r: r.start_date)
