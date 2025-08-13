from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.api.dependencies.user_role_manager import (
    UserRoleManager,
    get_user_role_manager,
)
from app.services.pegawai_service import PegawaiService
from app.utils.common import ErrorCode
from app.utils.exceptions import UnauthorizedError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


def unauthenticated_user_exception():
    print("[INFO] Gagal otentikasi pengguna")
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error_code": ErrorCode.UNAUTHORIZED,
            "message": "Token tidak valid",
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


class AuthHandler:
    def __init__(
        self, pegawai_service: PegawaiService, user_role_manager: UserRoleManager
    ) -> None:
        self.pegawai_service = pegawai_service
        self.user_role_manager = user_role_manager

    async def login(
        self,
        username_or_email: str,
        password: str,
    ):
        """Otentikasi pengguna dengan nama pengguna atau email dan kata sandi.

        Args:
            username_or_email (str): Nama pengguna atau email dari pengguna.
            password (str): Kata sandi dari pengguna.

        Raises:
            UnauthorizedError: Jika otentikasi gagal atau pengguna tidak ditemukan.
        """

        payload = await self.pegawai_service.login(username_or_email, password)

        if not payload:
            raise UnauthorizedError

        # get user info setelah mendapatkan token
        user_id = payload["user_id"]
        user_info = await self.pegawai_service.get_user_info(user_id)

        # Tidak ada user info yang di dapatkan dari service
        # ini bisa jadi user telah dihapus atau dinonaktifkan
        if not user_info:
            raise UnauthorizedError

        # buat user role jika belum ada
        await self.user_role_manager.create(user_id, user_info)

        return payload


async def validate_token(
    token: str = Depends(oauth2_scheme),
    pegawai_service: PegawaiService = Depends(PegawaiService),
):
    """verifikasi token ke service pegawai

    Args:
        token (str, optional): Token yang akan diverifikasi. Defaults to
            Depends(oauth2_scheme).
        pegawai_service (PegawaiService, optional): Service pegawai. Defaults to
            Depends(PegawaiService).

    Raises:
        unauthenticated_user_exception: Jika terjadi kesalahan saat memverifikasi
            token atau Jika token tidak valid.

    Returns:
        str: Token yang telah diverifikasi.
    """
    try:
        is_valid = await pegawai_service.validate_token(token)

        # validasi token ke service pegawai
        if not is_valid:
            raise unauthenticated_user_exception()
        return token

    except Exception:
        raise unauthenticated_user_exception() from None


async def auth_handler(
    pegawai_service: PegawaiService = Depends(PegawaiService),
    user_role_manager: UserRoleManager = Depends(get_user_role_manager),
):
    """Dependency untuk menginisialisasi AuthHandler."""

    return AuthHandler(pegawai_service, user_role_manager)
