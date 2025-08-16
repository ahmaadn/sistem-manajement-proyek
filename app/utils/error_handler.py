from collections import defaultdict
from traceback import print_exception
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.utils.common import ErrorCode
from app.utils.exceptions import AppException


def _response(
    *,
    status_code: int,
    error_code: ErrorCode | str,
    message: str,
    **extra: Any,
) -> JSONResponse:
    payload = {
        "error_code": str(error_code),
        "message": message,
        **extra,
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def global_exception_handler(_: Request, exc: Exception):
    print_exception(exc)
    return _response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        message="Terjadi kesalahan pada server. Silakan coba beberapa saat lagi.",
    )


def app_exception_handler(_: Request, exc: AppException):
    """Menangani kesalahan aplikasi."""
    return _response(
        status_code=getattr(exc, "status_code", status.HTTP_400_BAD_REQUEST),
        error_code=exc.error_code,
        message=exc.message,
        **exc.extra,
    )


def validation_exception_handler(_: Request, exc: RequestValidationError):
    """Menangani kesalahan validasi.."""

    reformatted_message = defaultdict(list)
    for pydantic_error in exc.errors():
        loc, msg = pydantic_error["loc"], pydantic_error["msg"]
        filtered_loc = loc[1:] if loc[0] in ("body", "query", "path") else loc

        if isinstance(filtered_loc, (tuple, list)):
            field_string = filtered_loc[0] if filtered_loc else "unknown"
        else:
            field_string = str(filtered_loc)

        reformatted_message[field_string].append(msg)

    return _response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code=ErrorCode.VALIDATION_ERROR,
        message="Permintaan tidak valid",
        errors=reformatted_message,
    )


def http_exception_handler(_: Request, exc: StarletteHTTPException):
    """Menangani Kelasahan"""

    if isinstance(exc.detail, dict):
        message = (
            exc.detail.get("message")
            or exc.detail.get("detail")
            or "Terjadi kesalahan."
        )
        error_code = exc.detail.get("error_code") or (
            ErrorCode.GENERIC_NOT_FOUND
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else ErrorCode.APP_ERROR
        )
        extra = {
            k: v
            for k, v in exc.detail.items()
            if k not in ("message", "detail", "error_code")
        }
    else:
        message = str(exc.detail)
        error_code = (
            ErrorCode.GENERIC_NOT_FOUND
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else ErrorCode.APP_ERROR
        )
        extra = {}

    return _response(
        status_code=exc.status_code,
        error_code=error_code,
        message=message,
        **extra,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(AppException, app_exception_handler)  # type: ignore
    app.add_exception_handler(RequestValidationError, validation_exception_handler)  # type: ignore
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)  # type: ignore
