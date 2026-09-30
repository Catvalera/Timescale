"""Pydantic-схемы ответов.

ASP.NET Core по умолчанию отдаёт JSON в camelCase (id, fileName, startDate ...),
поэтому здесь используется такой же формат полей.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class _CamelModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, alias_generator=to_camel, populate_by_name=True)


class ValueEntryOut(_CamelModel):
    id: int
    date: datetime
    execution_time: float
    value: float
    file_name: str


class ResultEntryOut(_CamelModel):
    id: int
    file_name: str
    time_delta_sec: float
    start_date: datetime
    avg_execution_time: float
    avg_value: float
    median_value: float
    max_value: float
    min_value: float
