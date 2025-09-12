import asyncio
import logging
import urllib.parse

from app.client import PegawaiApiClient
from app.schemas.user import UserBase

logger = logging.getLogger(__name__)


class PegawaiService:
    def __init__(self) -> None:
        self.client = PegawaiApiClient

    async def validate_token(self, token: str) -> bool:
        """Validasi token dengan mencocokkan pada FAKE_USERS."""
        result = await asyncio.gather(self.client.validation_token(token=token))
        return bool(result[0])

    async def get_user_info(self, user_id: int):
        """Ambil info user berdasarkan user_id."""
        result = await asyncio.gather(
            self.client.get_pegawai_detail(user_id=user_id)
        )
        user = result[0]
        if not user:
            return None
        return await self.map_to_pegawai_info(user.copy())

    async def get_user_info_by_token(self, token: str):
        """Ambil info user berdasarkan access_token, tanpa access_token di hasil."""
        result = await asyncio.gather(self.client.get_pegawai_me(token=token))
        user = result[0]
        if not user:
            return None
        return await self.map_to_pegawai_info(user.copy())

    async def login(self, email: str, password: str):
        """
        Login via BASE_API_PEGAWAI: POST {api_url}/login. Return access_token jika
        berhasil.
        """
        payload = {"email": email, "password": password}
        result = await asyncio.gather(self.client.login(payload=payload))
        return result[0]

    async def map_to_pegawai_info(self, data):
        """Map API response to UserBase.

        Args:
            data (dict): API response data.

        Returns:
            UserBase: Mapped UserBase object.
        """

        role = data.get("role")

        if role == "admin":
            name = data.get("email", "")
            position = role or ""
        else:
            # handle pegawai biasa
            pegawai = data.get("pegawai") or {
                "nama": data.get("email", ""),
                "position": data.get("position", role),
            }

            name = pegawai.get("nama", pegawai.get("nama_lengkap", ""))
            position = pegawai.get("jabatan", "")

        # handle profile_url
        profile_photo_path = data.get("profile_photo_path", None)
        if not profile_photo_path:
            safe_name = name.strip()
            encoded_name = urllib.parse.quote_plus(safe_name)
            profile_photo_path = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&bold=true&size=256"

        return UserBase(
            id=data.get("id"),
            name=name,
            employee_role=data.get("role"),
            email=data.get("email"),
            position=position,
            profile_url=profile_photo_path,
        )

    async def list_user(self) -> list[UserBase]:
        """Mendapatkan daftar semua pengguna.

        Returns:
            list[UserBase]: Daftar informasi pegawai.
        """
        result = await asyncio.gather(self.client.get_list_pegawai())
        result = result[0]
        if not result:
            return []

        users = result.get("data", [])
        return [await self.map_to_pegawai_info(user) for user in users]

    async def list_user_by_ids(self, data: list[int]) -> list[UserBase | None]:
        """Mendapatkan daftar user berdasarkan list ID yang diberikan.
        Jika suatu ID tidak ditemukan di data, kembalikan None pada posisi tersebut.

        Args:
            data (list[int]): Daftar ID pegawai.

        Returns:
            list[UserBase | None]: Daftar info pegawai atau None sesuai urutan ID.
        """
        result = await asyncio.gather(self.client.get_bulk_pegawai(ids=data))
        users = result[0]
        if not users or len(users) == 0:
            return []

        map_users = []
        for user in users:
            if user:
                map_users.append(await self.map_to_pegawai_info(user))
            else:
                map_users.append(None)
        return map_users


def _singleton(cls):
    _instances = {}

    def warp():
        if cls not in _instances:
            _instances[cls] = cls()
        return _instances[cls]

    return warp


PegawaiService = _singleton(PegawaiService)  # type: ignore
