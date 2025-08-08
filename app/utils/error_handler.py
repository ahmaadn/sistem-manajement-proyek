from traceback import print_exception

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import ValidationException
from fastapi.responses import JSONResponse

from app.utils.common import ErrorCode
from app.utils.exceptions import AppException


async def global_exception_handler(_: Request, ext: Exception):
    print_exception(ext)
    return JSONResponse(
        {
            "error_code": ErrorCode.INTERNAL_SERVER_ERROR,
            "messages": [
                "An internal server error occurred. Please try again later."
            ],
        },
        500,
    )


async def app_exception_handler(_: Request, ext: AppException):
    """Handle application-specific exceptions."""
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=ext.dump())


async def validation_exception_handler(_: Request, exc: ValidationException):
    """Handle validation exceptions globally."""
    details = exc.errors()
    modified_details = []
    for error in details:
        modified_details.append(
            {
                "loc": error["loc"],
                "messages": [error["msg"]],
                "error_code": error["type"].upper(),
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=jsonable_encoder({"details": modified_details}),
    )
