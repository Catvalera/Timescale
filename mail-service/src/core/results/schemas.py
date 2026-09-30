from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel


class ResultStatus(str, Enum):
    success = "success"
    error = "error"


class TokenData(BaseModel):
    access_token: str
    refresh_token: str


class ErrorData(BaseModel):
    code: int
    log: str


class ResultData(BaseModel):
    status: ResultStatus
    data: Optional[Any] = None
    token: Optional[TokenData] = None
    error: Optional[ErrorData] = None
