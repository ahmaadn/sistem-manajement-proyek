from typing import Callable

from fastapi import Depends

from app.api.dependencies.authentication import validate_token
from app.api.dependencies.repositories import get_user_repository
from app.api.dependencies.uow import get_uow
from app.db.models.role_model import Role
from app.db.repositories.user_repository import InterfaceUserRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.user import User
from app.services.pegawai_service import PegawaiService
from app.services.user_service import UserService
from app.utils import exceptions


async def get_user_service(
    pegawai_service: PegawaiService = Depends(PegawaiService),
    uow: UnitOfWork = Depends(get_uow),
    repo: InterfaceUserRepository = Depends(get_user_repository),
) -> UserService:
    """Mendapatkan instance UserService."""

    return UserService(pegawai_service=pegawai_service, uow=uow, repo=repo)


async def get_current_user(
    token: str = Depends(validate_token),
    pegawai_service: PegawaiService = Depends(PegawaiService),
    user_service: UserService = Depends(get_user_service),
) -> User:
    """Mendapatkan pengguna saat ini berdasarkan token yang diberikan.

    Args:
        token (str, optional): Token yang akan diverifikasi. Defaults to
            Depends(validate_token).
        pegawai_service (PegawaiService, optional): Service pegawai. Defaults to
            Depends(PegawaiService).
        user_service (UserService, optional): Service peran pengguna. Defaults to
            Depends(get_user_service).

    Raises:
        UnauthorizedError: Jika token tidak valid atau Jika pengguna
            tidak ditemukan.

    Returns:
        UserRead: Pengguna yang saat ini terautentikasi.
    """

    user_info = await pegawai_service.get_user_info_by_token(token)

    if user_info is None:
        raise exceptions.UnauthorizedError(
            "Pengguna tidak ditemukan atau token tidak valid."
        )

    user_role = await user_service.assign_role_to_user(user_info.id, user_info)

    return User(**user_info.model_dump(), role=Role(user_role.role))


async def get_user_admin(user: User = Depends(get_current_user)) -> User:
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
        raise exceptions.UnauthorizedError("User tidak memiliki akses admin.")
    return user


async def get_user_pm(user: User = Depends(get_current_user)) -> User:
    """Mendapatkan pengguna dengan peran PM.

    Args:
        user (UserRead, optional): Pengguna yang saat ini terautentikasi. Defaults to
            Depends(get_current_user).

    Raises:
        HTTPException: Jika pengguna tidak memiliki akses PM.

    Returns:
        UserRead: Pengguna dengan peran PM.
    """

    if user.role != Role.PROJECT_MANAGER:
        raise exceptions.UnauthorizedError("User tidak memiliki akses.")
    return user


async def get_user_member(user: User = Depends(get_current_user)) -> User:
    """Mendapatkan pengguna dengan peran anggota.

    Args:
        user (UserRead, optional): Pengguna yang saat ini terautentikasi. Defaults to
            Depends(get_current_user).

    Raises:
        HTTPException: Jika pengguna tidak memiliki akses anggota.

    Returns:
        UserRead: Pengguna dengan peran anggota.
    """

    if user.role != Role.TEAM_MEMBER:
        raise exceptions.UnauthorizedError("User tidak memiliki akses.")
    return user


def permission_required(roles: list[Role]) -> Callable[..., User]:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise exceptions.UnauthorizedError("User tidak memiliki akses.")
        return user

    return dependency
