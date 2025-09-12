import logging
from urllib.parse import urljoin

from app.core.config.settings import get_settings

logger = logging.getLogger(__name__)


class PegawaiApiUrls:
    BASE = get_settings().BASE_API_PEGAWAI.rstrip("/") + "/"
    """
    Base URL untuk layanan pegawai.
    """

    LOGIN = urljoin(BASE, "api/login")
    """
    URL endpoint untuk login. Gunakan metode POST dengan payload JSON
    berisi 'email' dan 'password'.
    """

    VALIDATION = urljoin(BASE, "api/auth/validation")
    """
    URL endpoint untuk validasi token. Gunakan metode POST dengan
    header Authorization.
    """

    PEGAWAI_ME = urljoin(BASE, "api/pegawai/me")
    """
    URL endpoint untuk mendapatkan data pegawai saat ini. Gunakan
    metode GET dengan header Authorization.
    """

    PEGAWAI_LIST = urljoin(BASE, "api/pegawai-list")
    """
    URL endpoint untuk mendapatkan daftar pegawai. Gunakan metode GET
    dengan header Authorization.
    """

    PEGAWAI_BULK = urljoin(BASE, "api/pegawai/bulk")
    """
    URL endpoint untuk melakukan operasi bulk pada pegawai. Gunakan
    metode POST dengan header Authorization dan payload JSON yang sesuai.
    """

    @staticmethod
    def pegawai_detail(user_id: int) -> str:
        """Bangun URL detail pegawai.

        Args:
            user_id: ID pengguna/pegawai.

        Returns:
            URL absolut endpoint detail pegawai.
        """
        return urljoin(PegawaiApiUrls.BASE, f"api/pegawai/{user_id}")
