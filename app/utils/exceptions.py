from typing import Any

from .common import ErrorCode


class AppException(Exception):  # noqa: N818
    def __init__(
        self, message: str, /, error_code: ErrorCode | None = None, **extra: Any
    ):
        if error_code is None:
            error_code = ErrorCode.APP_ERROR

        self.error_code = error_code
        self.message = message
        self.extra = extra

    def __str__(self):
        return (
            f"[{self.error_code}] {self.message}"
            if self.message
            else f"[{self.error_code}]"
        )

    def dump(self) -> dict[str, Any]:
        return {
            "error_code": str(self.error_code),
            "message": self.message,
            **self.extra,
        }
