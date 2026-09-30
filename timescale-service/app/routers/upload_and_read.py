"""Аналог Controllers/Upload_and_readController.cs."""
import logging
from pathlib import PurePath

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import ResultEntry, ValueEntry
from app.schemas import ResultEntryOut, ValueEntryOut
from app.services.csv_processing import ValidationError, aggregate, read_lines, validate

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Upload_and_read"])


@router.get("/Get_data_from_table_Value", response_model=list[ValueEntryOut])
async def get_value(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(ValueEntry).order_by(ValueEntry.id))
    return result.all()


@router.get("/Get_data_from_table_Result", response_model=list[ResultEntryOut])
async def get_result(session: AsyncSession = Depends(get_session)):
    result = await session.scalars(select(ResultEntry).order_by(ResultEntry.id))
    return result.all()


@router.post("/Upload_file", response_class=PlainTextResponse)
async def upload(file: UploadFile | None = File(None), session: AsyncSession = Depends(get_session)):
    logger.warning("Открытие файла")
    raw = await file.read() if file is not None else b""
    if file is None or not file.filename or len(raw) == 0:
        return PlainTextResponse("File is not selected", status_code=400)

    file_name = file.filename
    if PurePath(file_name).suffix.lower() != ".csv":
        return PlainTextResponse("Only files with the extension are allowed.csv", status_code=400)

    try:
        rows = validate(read_lines(raw))
    except (ValidationError, UnicodeDecodeError) as exc:
        logger.error("Ошибка валидации!")
        return PlainTextResponse(f"Error validation! {exc}", status_code=400)
    logger.info("Валидация прошла успешно!")

    agg = aggregate(rows)

    # Старые данные этого файла заменяются новыми — в одной транзакции для обеих таблиц.
    async with session.begin():
        await session.execute(delete(ValueEntry).where(ValueEntry.file_name == file_name))
        session.add_all(
            ValueEntry(date=r.date, execution_time=r.execution_time, value=r.value, file_name=file_name)
            for r in rows
        )

        await session.execute(delete(ResultEntry).where(ResultEntry.file_name == file_name))
        session.add(ResultEntry(
            file_name=file_name,
            time_delta_sec=agg.time_delta_sec,
            start_date=agg.start_date,
            avg_execution_time=agg.avg_execution_time,
            avg_value=agg.avg_value,
            median_value=agg.median_value,
            max_value=agg.max_value,
            min_value=agg.min_value,
        ))

    return f"Data successful upload from {file_name}"
