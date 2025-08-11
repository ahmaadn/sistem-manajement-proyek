# NOTE: untuk saat ini data menggunakan dummy dan tidak ada validasi

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.schemas.user import UserInfo
from app.services.pegawai_service import pegawai_service
from app.utils.common import ErrorCode

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def validate_token(token: str = Depends(oauth2_scheme)):
    try:
        is_valid = await pegawai_service.validate_token(token)

        # validasi token ke service pegawai
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": ErrorCode.UNAUTHORIZED,
                    "message": "Token tidak valid",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        return token

    except Exception:
        ...


async def get_current_user(token: str = Depends(validate_token)):
    try:
        user_info = await pegawai_service.get_user_info()

        return UserInfo(**user_info)
    except Exception:
        ...


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
