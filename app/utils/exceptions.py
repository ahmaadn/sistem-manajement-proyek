from typing import Any

from pydantic import BaseModel, Field

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


class AppErrorResponse(BaseModel):
    error_code: str = Field(
        description="Kode kesalahan yang menunjukkan jenis kesalahan aplikasi."
    )
    message: str = Field(
        description="Pesan kesalahan yang memberikan rincian lebih lanjut tentang kesalahan aplikasi."  # noqa: E501
    )


class ValidationErrorResponse(BaseModel):
    error_code: str = Field(
        description="Kode kesalahan yang menunjukkan jenis kesalahan validasi."
    )
    message: str = Field(
        description=(
            "Pesan kesalahan yang memberikan rincian lebih lanjut "
            "tentang kesalahan validasi."
        )
    )
    errors: dict[str, list[str]] = Field(
        description="Sebuah kamus yang berisi kesalahan validasi untuk setiap field."
    )


class UnauthorizedError(AppException):
    """Kesalahan otorisasi."""

    def __init__(
        self,
        message: str = "username atau password salah",
        /,
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED,
        **extra: Any,
    ):
        super().__init__(message, error_code, **extra)


class ItemNotFoundError(AppException):
    """Kesalahan ketika proyek tidak ditemukan."""

    def __init__(
        self,
        message: str,
        /,
        error_code: ErrorCode = ErrorCode.PROYEK_NOT_FOUND,
        **extra: Any,
    ):
        super().__init__(message, error_code, **extra)
