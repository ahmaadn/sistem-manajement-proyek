import asyncio
import logging
import urllib.parse

from starlette_context import context

from app.client import PegawaiAiohttpClient
from app.schemas.user import UserBase

logger = logging.getLogger(__name__)


class PegawaiService:
    def __init__(self) -> None:
        # menggunakan aiohttp client sebagai default
        # bisa juga menggunakan httpx client jika diperlukan
        self.client = PegawaiAiohttpClient

    def _get_ctx_cache(self) -> dict:
        """
        Ambil cache user per-request dari starlette_context.
        Selalu mengembalikan dict dan memastikan context terisi.
        """
        cache = context.get("user_info_cache")
        if not isinstance(cache, dict):
            cache = {}
            context["user_info_cache"] = cache
        return cache

    async def validate_token(self, token: str) -> bool:
        """Validasi token Bearer ke layanan Pegawai.

        Args:
            token (str): Token Bearer eksplisit (opsional). Jika tidak ada,
                fallback ke header Authorization request. Default to None

        Returns:
            bool: True jika valid (HTTP 200), False jika tidak valid atau terjadi
                error.
        """

        cache = self._get_ctx_cache()
        tkey = f"token_valid:{token}"
        if tkey in cache:
            return bool(cache[tkey])

        result = await asyncio.gather(self.client.validation_token(token=token))
        is_valid = bool(result[0])
        cache[tkey] = is_valid
        return is_valid

    async def get_user_info(self, user_id: int):
        """Ambil info user berdasarkan user_id.

        Args:
            user_id (int): ID pengguna/pegawai.

        Returns:
            UserBase | None: Objek informasi pegawai jika ditemukan, None jika tidak.
        """
        cache = self._get_ctx_cache()
        ckey = f"id:{user_id}"
        if ckey in cache:
            logger.debug(f"Cache hit for user_id {user_id}")
            return cache[ckey]

        result = await asyncio.gather(
            self.client.get_pegawai_detail(user_id=user_id)
        )
        user = result[0]
        if not user:
            cache[ckey] = None
            return None
        mapped = await self.map_to_pegawai_info(user.copy())
        cache[ckey] = mapped
        return mapped

    async def get_user_info_by_token(self, token: str):
        """Ambil info user berdasarkan token.

        Args:
            token (str): Token Bearer eksplisit (opsional). Jika tidak ada,
                fallback ke header Authorization request. Default to None.

        Returns:
            UserBase | None: Objek informasi pegawai jika ditemukan, None jika tidak.
        """
        cache = self._get_ctx_cache()
        tkey = f"token:{token}"
        if tkey in cache:
            return cache[tkey]

        result = await asyncio.gather(self.client.get_pegawai_me(token=token))
        user = result[0]

        if not user:
            cache[tkey] = None
            return None

        mapped = await self.map_to_pegawai_info(user.copy())
        cache[tkey] = mapped

        # simpan juga berdasarkan id jika tersedia
        uid = getattr(mapped, "id", None)
        if uid is not None:
            cache[f"id:{uid}"] = mapped
        return mapped

    async def login(self, email: str, password: str):
        """Lakukan login dan ambil token akses.

        Args:
            email (str): Alamat email pengguna.
            password (str): Kata sandi pengguna.

        Returns:
            dict[str, Any] | None: Berisi 'access_token', 'user', dan 'user_id'
                jika sukses; None jika gagal/format tak sesuai.
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
        result = (await asyncio.gather(self.client.get_list_pegawai()))[0]
        if not result:
            return []

        users = result.get("data", [])
        cache = self._get_ctx_cache()
        mapped_list: list[UserBase] = []
        for raw in users:
            mapped = await self.map_to_pegawai_info(raw)
            mapped_list.append(mapped)
            uid = getattr(mapped, "id", None)
            if uid is not None:
                cache[f"id:{uid}"] = mapped
        return mapped_list

    async def list_user_by_ids(self, data: list[int]) -> list[UserBase | None]:
        """Mendapatkan daftar user berdasarkan list ID yang diberikan.
        Jika suatu ID tidak ditemukan di data, kembalikan None pada posisi tersebut.

        Args:
            data (list[int]): Daftar ID pegawai.

        Returns:
            list[UserBase | None]: Daftar info pegawai atau None sesuai urutan ID.
        """
        if not data:
            return []

        cache = self._get_ctx_cache()

        # Ambil dari cache dulu
        result_list: list[UserBase | None] = []
        missing_ids: list[int] = []

        for uid in data:
            cval = cache.get(f"id:{uid}")

            # jika tidak ada di cache, tandai untuk fetch
            if cval is None and f"id:{uid}" not in cache:
                missing_ids.append(uid)

            # isi result_list dengan nilai dari cache atau None
            result_list.append(cval if f"id:{uid}" in cache else None)

        logger.debug("Cache miss for user_id %s (need fetch)", missing_ids)

        # Fetch yang belum ada
        fetched: list[dict | None] = []
        if missing_ids:
            fetched = (
                await asyncio.gather(self.client.get_bulk_pegawai(ids=missing_ids))
            )[0] or []

        # Map fetched ke cache
        idx = 0
        for i, uid in enumerate(data):
            if result_list[i] is not None or f"id:{uid}" in cache:
                continue

            raw = fetched[idx] if idx < len(fetched) else None
            idx = 1
            if raw:
                mapped = await self.map_to_pegawai_info(raw)
                cache[f"id:{uid}"] = mapped
                result_list[i] = mapped
            else:
                cache[f"id:{uid}"] = None
                result_list[i] = None

        return result_list


def _singleton(cls):
    _instances = {}

    def warp():
        if cls not in _instances:
            _instances[cls] = cls()
        return _instances[cls]

    return warp


PegawaiService = _singleton(PegawaiService)  # type: ignore
