"""Разбор, валидация CSV и расчёт агрегатов.

Логика перенесена из Upload_and_readController.cs (методы validation и add_data_in_Result).
"""
import logging
import math
import statistics
from dataclasses import dataclass
from datetime import datetime, time, timezone

logger = logging.getLogger(__name__)

MIN_DATE = datetime(2000, 1, 1, tzinfo=timezone.utc)
MIN_ROWS_EXCLUSIVE = 1      # строк данных должно быть > 1
MAX_ROWS_EXCLUSIVE = 10000  # и < 10000


@dataclass(frozen=True)
class Row:
    date: datetime
    execution_time: float
    value: float


@dataclass(frozen=True)
class Aggregates:
    time_delta_sec: float
    start_date: datetime
    avg_execution_time: float
    avg_value: float
    median_value: float
    max_value: float
    min_value: float


class ValidationError(Exception):
    pass


def read_lines(raw: bytes) -> list[str]:
    """Читает файл как UTF-8 (BOM допускается) и возвращает строки без заголовка."""
    text = raw.decode("utf-8-sig")
    lines = text.splitlines()
    return lines[1:]


def _parse_date(s: str) -> datetime:
    dt = datetime.fromisoformat(s.strip())
    # Дата без часового пояса считается UTC; с поясом — приводится к UTC
    # (аналог DateTimeStyles.AdjustToUniversal).
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_number(s: str) -> float:
    # Аналог double.TryParse(..., NumberStyles.Float, CultureInfo.InvariantCulture):
    # разделитель — точка, NaN/Infinity не принимаются.
    v = float(s.strip())
    if not math.isfinite(v):
        raise ValueError("not a finite number")
    return v


def validate(lines: list[str], now: datetime | None = None) -> list[Row]:
    """Проверяет строки CSV. При любой ошибке выбрасывает ValidationError."""
    if not (MIN_ROWS_EXCLUSIVE < len(lines) < MAX_ROWS_EXCLUSIVE):
        msg = f"Количество строк ({len(lines)}) должно быть больше {MIN_ROWS_EXCLUSIVE} и меньше {MAX_ROWS_EXCLUSIVE}!"
        logger.error(msg)
        raise ValidationError(msg)

    now = now or datetime.now(timezone.utc)
    # Как и в C#-версии: верхняя граница — начало текущих суток (UTC).
    max_date = datetime.combine(now.date(), time.min, tzinfo=timezone.utc)

    rows: list[Row] = []
    for line_no, line in enumerate(lines, start=2):
        parts = line.split(";")
        if len(parts) < 3:
            msg = f"Строка {line_no}: ожидается 3 колонки, разделённые ';'!"
            logger.error(msg)
            raise ValidationError(msg)

        try:
            dt = _parse_date(parts[0])
        except ValueError:
            msg = f"Строка {line_no}: ошибка преобразования строки в дату!"
            logger.error(msg)
            raise ValidationError(msg) from None

        if dt < MIN_DATE or dt > max_date:
            msg = (f"Строка {line_no}: дата {dt} не удовлетворяет условиям, "
                   f"{dt} >= {MIN_DATE} и {dt} <= {max_date}!")
            logger.error(msg)
            raise ValidationError(msg)

        try:
            execution_time = _parse_number(parts[1])
            value = _parse_number(parts[2])
        except ValueError:
            msg = f"Строка {line_no}: ошибка преобразования строки в число!"
            logger.error(msg)
            raise ValidationError(msg) from None

        if execution_time < 0 or value < 0:
            msg = f"Строка {line_no}: отрицательные значения не допустимы!"
            logger.error(msg)
            raise ValidationError(msg)

        rows.append(Row(dt, execution_time, value))

    return rows


def aggregate(rows: list[Row]) -> Aggregates:
    """Расчёт итоговой строки для таблицы Results."""
    dates = [r.date for r in rows]
    times = [r.execution_time for r in rows]
    values = [r.value for r in rows]

    date_min, date_max = min(dates), max(dates)
    # round() в Python, как и Math.Round в C#, использует банковское округление.
    return Aggregates(
        time_delta_sec=(date_max - date_min).total_seconds(),
        start_date=date_min,
        avg_execution_time=round(statistics.fmean(times), 4),
        avg_value=round(statistics.fmean(values), 4),
        median_value=round(statistics.median(values), 4),
        max_value=max(values),
        min_value=min(values),
    )
