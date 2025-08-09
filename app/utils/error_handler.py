from collections import defaultdict
from traceback import print_exception

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.utils.common import ErrorCode
from app.utils.exceptions import AppException


async def global_exception_handler(_: Request, ext: Exception):
    print_exception(ext)
    return JSONResponse(
        {
            "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
            "message": "An internal server error occurred. Please try again later.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


async def app_exception_handler(_: Request, ext: AppException):
    """Menangani kesalahan aplikasi."""
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ext.dump())


async def validation_exception_handler(_: Request, exc: RequestValidationError):
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

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=jsonable_encoder(
            {
                "error_code": ErrorCode.VALIDATION_ERROR,
                "message": "Invalid request",
                "errors": reformatted_message,
            }
        ),
    )
