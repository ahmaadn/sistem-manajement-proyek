from typing import Any

from fastapi import status
from pydantic import BaseModel, Field

from .common import ErrorCode


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


class AppException(Exception):  # noqa: N818
    def __init__(
        self,
        message: str,
        /,
        error_code: ErrorCode | None = None,
        *,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        **extra: Any,
    ):
        if error_code is None:
            error_code = ErrorCode.APP_ERROR

        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.headers = headers
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


class UnauthorizedError(AppException):
    def __init__(
        self,
        message: str = "email atau password salah",
        /,
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_401_UNAUTHORIZED, **extra
        )


class ProjectNotFoundError(AppException):
    def __init__(
        self,
        message: str = "Proyek tidak ditemukan",
        /,
        error_code: ErrorCode = ErrorCode.PROJECT_NOT_FOUND,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_404_NOT_FOUND, **extra
        )


class MemberAlreadyExistsError(AppException):
    def __init__(
        self,
        message: str = "Anggota sudah terdaftar di proyek",
        /,
        error_code: ErrorCode = ErrorCode.MEMBER_ALREADY_JOIN,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_406_NOT_ACCEPTABLE, **extra
        )


class MemberNotFoundError(AppException):
    def __init__(
        self,
        message: str = "Anggota proyek tidak ditemukan",
        /,
        error_code: ErrorCode = ErrorCode.MEMBER_NOT_FOUND,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_404_NOT_FOUND, **extra
        )


class CannotRemoveMemberError(AppException):
    def __init__(
        self,
        message: str = "Tidak dapat menghapus anggota proyek",
        /,
        error_code: ErrorCode = ErrorCode.MEMBER_CANNOT_REMOVE,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_406_NOT_ACCEPTABLE, **extra
        )


class TaskNotFoundError(AppException):
    def __init__(
        self,
        message: str = "Tugas tidak ditemukan",
        /,
        error_code: ErrorCode = ErrorCode.TASK_NOT_FOUND,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_404_NOT_FOUND, **extra
        )


class UserNotFoundError(AppException):
    def __init__(
        self,
        message: str = "Pengguna tidak ditemukan",
        /,
        error_code: ErrorCode = ErrorCode.USER_NOT_FOUND,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_404_NOT_FOUND, **extra
        )


class InvalidRoleAssignmentError(AppException):
    def __init__(
        self,
        message: str = "Peran tidak valid untuk pengguna",
        /,
        error_code: ErrorCode = ErrorCode.INVALID_ROLE_ASSIGNMENT,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_406_NOT_ACCEPTABLE, **extra
        )


class UserNotInProjectError(AppException):
    def __init__(
        self,
        message: str = "Pengguna tidak terdaftar di proyek",
        /,
        error_code: ErrorCode = ErrorCode.USER_NOT_IN_PROJECT,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_403_FORBIDDEN, **extra
        )


class CannotChangeRoleError(AppException):
    def __init__(
        self,
        message: str = "Tidak bisa mwwerubah role",
        /,
        error_code: ErrorCode = ErrorCode.CANNOT_CHANGE_ROLE_PROJECT,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_403_FORBIDDEN, **extra
        )


class ForbiddenError(AppException):
    def __init__(
        self,
        message: str = "Akses ditolak",
        /,
        error_code: ErrorCode = ErrorCode.FORBIDDEN,
        **extra: Any,
    ):
        super().__init__(
            message, error_code, status_code=status.HTTP_403_FORBIDDEN, **extra
        )
