from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)


class AuthHandler:
    def __init__(self, pegawai_service: PegawaiService) -> None:
        self.pegawai_service = pegawai_service

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
            raise exceptions.UnauthorizedError

        # get user info setelah mendapatkan token
        user_id = payload["user_id"]
        user_info = await self.pegawai_service.get_user_info(user_id)

        # Tidak ada user info yang di dapatkan dari service
        # ini bisa jadi user telah dihapus atau dinonaktifkan
        if not user_info:
            raise exceptions.UnauthorizedError

        return payload, user_info


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
    is_valid = await pegawai_service.validate_token(token)

    # validasi token ke service pegawai
    if not is_valid:
        raise exceptions.UnauthorizedError(
            "Token tidak valid", headers={"WWW-Authenticate": "Bearer"}
        )
    return token


async def auth_handler(pegawai_service: PegawaiService = Depends(PegawaiService)):
    """Dependency untuk menginisialisasi AuthHandler."""

    return AuthHandler(pegawai_service)
