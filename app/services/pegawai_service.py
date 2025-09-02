# NOTE: untuk semntara menggunakan data dummy
# implementasi service pegawai akan di kerjakan setalah
# api dari sistem pegawai siap digunakan

import asyncio
import logging
from time import time
from typing import Any
import urllib.parse

import aiohttp

from app.core.config.settings import get_settings
from app.middleware.request import request_object
from app.schemas.user import PegawaiInfo

logger = logging.getLogger(__name__)

FAKE_USERS = [
    {
        "access_token": "dummy_access_token_1",
        "user_id": 1,
        "nama": "Admin",
        "role": "admin",
        "email": "admin@example.com",
        "jabatan": "Kepala Admin",
        "unit_kerja": "Manajemen",
        "alamat": "Jl. Admin No. 1",
        "profile_url": "https://randomuser.me/api/portraits/lego/6.jpg",
    },
    {
        "access_token": "dummy_access_token_2",
        "user_id": 2,
        "nama": "HRD",
        "role": "hrd",
        "email": "hrd@example.com",
        "jabatan": "HRD Manager",
        "unit_kerja": "HRD",
        "alamat": "Jl. HRD No. 2",
        "profile_url": "https://randomuser.me/api/portraits/lego/4.jpg",
    },
    {
        "access_token": "dummy_access_token_3",
        "user_id": 3,
        "nama": "Pegawai Satu",
        "role": "pegawai",
        "email": "pegawai1@example.com",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 3",
        "profile_url": "https://randomuser.me/api/portraits/lego/0.jpg",
    },
    {
        "access_token": "dummy_access_token_4",
        "user_id": 4,
        "nama": "Pegawai Dua",
        "role": "pegawai",
        "email": "pegawai2@example.com",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 4",
        "profile_url": "https://randomuser.me/api/portraits/lego/2.jpg",
    },
    {
        "access_token": "dummy_access_token_5",
        "user_id": 5,
        "nama": "Pegawai Tiga",
        "role": "pegawai",
        "email": "pegawai3@example.com",
        "jabatan": "Staff",
        "unit_kerja": "Operasional",
        "alamat": "Jl. Pegawai No. 5",
        "profile_url": "https://randomuser.me/api/portraits/lego/8.jpg",
    },
]


def _get_bearer_from_ctx() -> str | None:
    """Ambil Bearer token dari request saat ini (Authorization header)."""
    try:
        req = request_object.get()
    except Exception:
        return None
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth:
        return None
    parts = auth.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None

class _PegawaiApiClient:

    @staticmethod
    async def login(*, payload: dict[str, Any]) -> dict[str, Any] | None:
            request = request_object.get()
            try:
                start_time = time()
                async with request.app.requests_client.post(  # type: ignore
                    "api/login", json=payload
                ) as res:
                    res.raise_for_status()
                    data = await res.json()

                    # mendapatkan token
                    token = data.get("token").split("|")[-1]

                    # get data user
                    user = data.get("user")
                    user_id = user.get("id")

                    logger.debug("response login: %s", data)
                    logger.debug("time request /api/login: %s", time() - start_time)
                    return {"access_token": token, "user": user, "user_id": user_id}
            except (ValueError, aiohttp.ClientError) as e:
                logger.error("Error during login request: %s", e)
                return None

    @staticmethod
    async def validation_token(*, token: str | None = None):
        token = token or _get_bearer_from_ctx()
        if not token:
            logger.warning("get_pegawai_me: token tidak tersedia di context/header.")
            return None
        try:
            start_time = time()
            async with request.app.requests_client.post(  # type: ignore
                "api/auth/validation", headers={"Authorization": f"Bearer {token}"}
            ) as res:
                res.raise_for_status()
                data = await res.json()

                logger.debug("response validate_token: %s", data)
                logger.debug("time request /auth/validation: %s", time() - start_time)
                return True
        except (ValueError, aiohttp.ClientError) as e:
            logger.error("Error during validate_token request: %s", e)
            return False

    @staticmethod
    async def get_pegawai_me(*, token: str | None = None):
        token = token or _get_bearer_from_ctx()
        if not token:
            logger.warning("get_pegawai_me: token tidak tersedia di context/header.")
            return None
        request = request_object.get()
        try:
            start_time = time()
            async with request.app.requests_client.get(  # type: ignore
                "api/pegawai/me", headers={"Authorization": f"Bearer {token}"}
            ) as res:
                res.raise_for_status()
                data = await res.json()
                logger.debug("response get_pegawai_me: %s", data)
                logger.debug("time request /pegawai/me: %s", time() - start_time)
                return data
        except (ValueError, aiohttp.ClientError) as e:
            logger.error("Error during get_pegawai_me request: %s", e)
            return None

class PegawaiService:
    def __init__(self) -> None:
        self.api_url = get_settings().API_PEGAWAI

    async def validate_token(self, token: str) -> bool:
        """Validasi token dengan mencocokkan pada FAKE_USERS."""
        result = await asyncio.gather(_PegawaiApiClient.validation_token(token=token))
        return result[0]

    async def get_user_info(self, user_id: int):
        """Ambil info user berdasarkan user_id, tanpa access_token."""
        user = next((u for u in FAKE_USERS if u["user_id"] == user_id), None)
        if not user:
            return None
        return self._map_to_user_profile(user.copy())

    async def get_user_info_by_token(self, token: str):
        """Ambil info user berdasarkan access_token, tanpa access_token di hasil."""
        result = await asyncio.gather(_PegawaiApiClient.get_pegawai_me(token=token))
        user = result[0]
        if not user:
            return None
        return await self.map_to_pegawai_info(user.copy())

    async def login(self, email: str, password: str):
        """
        Login via API_PEGAWAI: POST {api_url}/login. Return access_token jika
        berhasil.
        """
        payload = {"email": email, "password": password}
        result = await asyncio.gather(_PegawaiApiClient.login(payload=payload))
        return result[0]

    async def map_to_pegawai_info(self, data):
        """Map API response to PegawaiInfo.

        Args:
            data (dict): API response data.

        Returns:
            PegawaiInfo: Mapped PegawaiInfo object.
        """

        role = data.get("role")

        if role == 'admin':
            name = data['email']
            position = data['role']
        else:
        # handle pegawai
            pegawai = data.get("pegawai")
            if not pegawai:
                pegawai = {
                    'nama': data.get('email'),
                    'position': data.get('position')
                }
            name = pegawai['nama']
            position = pegawai['jabatan']

        # handle profile_url
        profile_photo_path = data.get("profile_photo_path")
        safe_name = name.strip()
        encoded_name = urllib.parse.quote_plus(safe_name)
        dummy_profile_url = f"https://ui-avatars.com/api/?name={encoded_name}&background=random&bold=true&size=256"

        return PegawaiInfo(
            id=data.get("id"),
            name=name,
            employee_role=data.get("role"),
            email=data.get("email"),
            position=position,
            # work_unit=data.get("unit_kerja"),
            # address=data.get("alamat"),
            profile_url=profile_photo_path or dummy_profile_url,
        )

    def _map_to_user_profile(self, data):
        return PegawaiInfo(
            id=data.get("user_id"),
            name=data.get("nama"),
            employee_role=data.get("role"),
            email=data.get("email"),
            position=data.get("jabatan"),
            # work_unit=data.get("unit_kerja"),
            # address=data.get("alamat"),
            profile_url=data.get("profile_url"),
        )

    async def list_user(self) -> list[PegawaiInfo]:
        """Mendapatkan daftar semua pengguna.

        Returns:
            list[PegawaiInfo]: Daftar informasi pegawai.
        """
        return [self._map_to_user_profile(user) for user in FAKE_USERS]

    async def list_user_by_ids(self, data: list[int]) -> list[PegawaiInfo | None]:
        """Mendapatkan daftar user berdasarkan list ID yang diberikan.
        Jika suatu ID tidak ditemukan di data, kembalikan None pada posisi tersebut.

        Args:
            data (list[int]): Daftar ID pegawai.

        Returns:
            list[PegawaiInfo | None]: Daftar info pegawai atau None sesuai urutan ID.
        """
        result: list[PegawaiInfo | None] = []
        for user_id in data:
            user = next((u for u in FAKE_USERS if u["user_id"] == user_id), None)
            result.append(self._map_to_user_profile(user.copy()) if user else None)
        return result


def _singleton(cls):
    _instances = {}

    def warp():
        if cls not in _instances:
            _instances[cls] = cls()
        return _instances[cls]

    return warp


PegawaiService = _singleton(PegawaiService)  # type: ignore
