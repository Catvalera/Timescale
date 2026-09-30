"""ORM-модели (аналог Models/ValueEntry.cs и Models/ResultEntry.cs).

Имена таблиц и колонок совпадают с C#-версией (EF Core создаёт их в PascalCase),
поэтому обе реализации могут работать с одной и той же базой.
"""
from datetime import datetime

from sqlalchemy import DateTime, Double, Identity, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ValueEntry(Base):
    __tablename__ = "Values"

    id: Mapped[int] = mapped_column("Id", Integer, Identity(), primary_key=True)
    date: Mapped[datetime] = mapped_column("Date", DateTime(timezone=True), nullable=False)
    execution_time: Mapped[float] = mapped_column("ExecutionTime", Double, nullable=False)
    value: Mapped[float] = mapped_column("Value", Double, nullable=False)
    file_name: Mapped[str] = mapped_column("FileName", Text, nullable=False, default="")


class ResultEntry(Base):
    __tablename__ = "Results"

    id: Mapped[int] = mapped_column("Id", Integer, Identity(), primary_key=True)
    file_name: Mapped[str] = mapped_column("FileName", Text, nullable=False, default="")
    time_delta_sec: Mapped[float] = mapped_column("TimeDeltaSec", Double, nullable=False)
    start_date: Mapped[datetime] = mapped_column("StartDate", DateTime(timezone=True), nullable=False)
    avg_execution_time: Mapped[float] = mapped_column("AvgExecutionTime", Double, nullable=False)
    avg_value: Mapped[float] = mapped_column("AvgValue", Double, nullable=False)
    median_value: Mapped[float] = mapped_column("MedianValue", Double, nullable=False)
    max_value: Mapped[float] = mapped_column("MaxValue", Double, nullable=False)
    min_value: Mapped[float] = mapped_column("MinValue", Double, nullable=False)
