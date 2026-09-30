from dataclasses import dataclass, field

from src.core.results import ResultData, ResultStatus, TokenData


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str

    @classmethod
    def empty(cls) -> "TokenPair":
        return cls(access_token="", refresh_token="")

    def to_result(self) -> ResultData:
        return ResultData(
            status=ResultStatus.success,
            token=TokenData(access_token=self.access_token, refresh_token=self.refresh_token),
        )


@dataclass(frozen=True, slots=True)
class AuthResult:
    access_token: str
    refresh_token: str = ""
    need_verify: bool = False
    data: dict = field(default_factory=dict)

    def to_result(self) -> ResultData:
        return ResultData(
            status=ResultStatus.success,
            data={"requires_verification": self.need_verify, **self.data},
            token=TokenData(access_token=self.access_token, refresh_token=self.refresh_token),
        )
