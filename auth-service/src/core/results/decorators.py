from functools import wraps
from typing import Protocol, runtime_checkable

from .schemas import ResultData, ResultStatus


@runtime_checkable
class ToResult(Protocol):
    def to_result(self) -> ResultData: ...


def standard_response(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        payload = await func(*args, **kwargs)
        if isinstance(payload, ToResult):
            return payload.to_result()
        return ResultData(status=ResultStatus.success, data=payload)

    return wrapper
