from functools import wraps

from .schemas import ResultData, ResultStatus


def standard_response(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return ResultData(
            status=ResultStatus.success,
            data=await func(*args, **kwargs),
        )

    return wrapper
