"""Аналог Controllers/Filter_dataController.cs."""
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ResultEntry
from app.schemas import ResultEntryOut

router = APIRouter(tags=["Filter_data"])

DATE_HINT = "Формат: YYYY-mm-dd (пример: 2025-03-03)"


@router.get("/Sort_by_filename", response_model=list[ResultEntryOut])
async def get_from_filename(name: str, session: AsyncSession = Depends(get_session)):
    stmt = (select(ResultEntry)
            .where(ResultEntry.file_name.contains(name, autoescape=True))
            .order_by(ResultEntry.id))
    return (await session.scalars(stmt)).all()


@router.get("/Sort_by_StartDate", response_model=list[ResultEntryOut])
async def get_from_date(
    startdate: datetime = Query(description=DATE_HINT, examples=["2025-03-03"]),
    enddate: datetime = Query(description=DATE_HINT, examples=["2025-08-03"]),
    session: AsyncSession = Depends(get_session),
):
    # Сравнение только по дате (UTC), включительно с обеих сторон — как StartDate.Date в C#.
    start = datetime.combine(startdate.date(), time.min, tzinfo=timezone.utc)
    end_exclusive = datetime.combine(enddate.date(), time.min, tzinfo=timezone.utc) + timedelta(days=1)
    stmt = (select(ResultEntry)
            .where(ResultEntry.start_date >= start, ResultEntry.start_date < end_exclusive)
            .order_by(ResultEntry.id))
    return (await session.scalars(stmt)).all()


@router.get("/Sort_by_avg-Value", response_model=list[ResultEntryOut])
async def get_from_avgvalue(startValue: float, endValue: float, session: AsyncSession = Depends(get_session)):
    stmt = (select(ResultEntry)
            .where(ResultEntry.avg_value >= startValue, ResultEntry.avg_value <= endValue)
            .order_by(ResultEntry.id))
    return (await session.scalars(stmt)).all()


@router.get("/Sort_by_avg-ExecutionTime", response_model=list[ResultEntryOut])
async def get_from_avgexecutiontime(startValue: float, endValue: float, session: AsyncSession = Depends(get_session)):
    stmt = (select(ResultEntry)
            .where(ResultEntry.avg_execution_time >= startValue, ResultEntry.avg_execution_time <= endValue)
            .order_by(ResultEntry.id))
    return (await session.scalars(stmt)).all()
