"""Аналог Controllers/Table_actionsController.cs."""
from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session

router = APIRouter(prefix="/api/Table_actions", tags=["Table_actions"])


@router.delete("/clear_table_Value", response_class=PlainTextResponse)
async def clear_all_values(session: AsyncSession = Depends(get_session)):
    # Удаляет все строки и сбрасывает счётчик Id на 1.
    async with session.begin():
        await session.execute(text('TRUNCATE TABLE "Values" RESTART IDENTITY'))
    return "All records deleted."


@router.delete("/clear_table_Result", response_class=PlainTextResponse)
async def clear_all_results(session: AsyncSession = Depends(get_session)):
    async with session.begin():
        await session.execute(text('TRUNCATE TABLE "Results" RESTART IDENTITY'))
    return "All records deleted."
