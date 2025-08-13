# NOTE: untuk saat ini data menggunakan dummy dan tidak ada validasi

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.user import UserInfo
from app.services.pegawai_service import PegawaiService
from app.utils.common import ErrorCode

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


def unauthenticated_user_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_code": ErrorCode.UNAUTHORIZED,
            "message": "Token tidak valid",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


async def validate_token(
    token: str = Depends(oauth2_scheme),
    pegawai_service: PegawaiService = Depends(PegawaiService),
):
    try:
        is_valid = await pegawai_service.validate_token(token)

        # validasi token ke service pegawai
        if not is_valid:
            raise unauthenticated_user_exception()
        return token

    except Exception:
        raise unauthenticated_user_exception() from None


async def get_current_user(
    token: str = Depends(validate_token),
    pegawai_service: PegawaiService = Depends(PegawaiService),
):
    try:
        user_info = await pegawai_service.get_user_info_by_token(token)

        if user_info is None:
            raise unauthenticated_user_exception()

        return user_info
    except Exception as e:
        print("Error getting current user:", str(e))
        raise unauthenticated_user_exception() from None


async def get_user_admin(user: UserInfo = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED,
                "message": "User tidak memiliki akses admin",
            },
        )
    return user
