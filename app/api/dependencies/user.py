from fastapi import Depends, HTTPException, status

from app.api.dependencies.authentication import (
    unauthenticated_user_exception,
    validate_token,
)
from app.api.dependencies.user_role_manager import (
    UserRoleManager,
    get_user_role_manager,
)
from app.db.models.role_model import Role
from app.schemas.user import UserRead
from app.services.pegawai_service import PegawaiService
from app.utils.common import ErrorCode


async def get_current_user(
    token: str = Depends(validate_token),
    pegawai_service: PegawaiService = Depends(PegawaiService),
    user_role_manager: UserRoleManager = Depends(get_user_role_manager),
) -> UserRead:
    """Mendapatkan pengguna saat ini berdasarkan token yang diberikan.

    Args:
        token (str, optional): Token yang akan diverifikasi. Defaults to
            Depends(validate_token).
        pegawai_service (PegawaiService, optional): Service pegawai. Defaults to
            Depends(PegawaiService).
        user_role_manager (UserRoleManager, optional): Manager peran pengguna.
            Defaults to Depends(get_user_role_manager).

    Raises:
        unauthenticated_user_exception: Jika token tidak valid atau Jika pengguna
            tidak ditemukan.

    Returns:
        UserRead: Pengguna yang saat ini terautentikasi.
    """

    try:
        user_info = await pegawai_service.get_user_info_by_token(token)

        if user_info is None:
            raise unauthenticated_user_exception()

        user_role = await user_role_manager.create(user_info.id, user_info)

        return UserRead(**user_info.model_dump(), role=Role(user_role.role))

    except Exception as e:
        print("Error getting current user:", str(e))
        raise unauthenticated_user_exception() from None


async def get_user_admin(user: UserRead = Depends(get_current_user)):
    """Mendapatkan pengguna dengan peran admin.

    Args:
        user (UserRead, optional): Pengguna yang saat ini terautentikasi. Defaults to
            Depends(get_current_user).

    Raises:
        HTTPException: Jika pengguna tidak memiliki akses admin.

    Returns:
        UserRead: Pengguna dengan peran admin.
    """

    if user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error_code": ErrorCode.UNAUTHORIZED,
                "message": "User tidak memiliki akses",
            },
        )
    return user


async def permission_required(roles):
    def dependency(user: UserRead = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error_code": ErrorCode.UNAUTHORIZED,
                    "message": "User tidak memiliki akses",
                },
            )
        return user

    return dependency
