import asyncio
from typing import Any, Optional, Unpack

import aiohttp

SIZE_POOL_AIOHTTP = 100


class SingletonAiohttp:
    """Pengelola global ClientSession aiohttp per event loop.

    Menjaga satu instance ClientSession aktif untuk loop berjalan saat ini.
    Jika loop berubah atau sesi tertutup, sesi baru akan dibuat.
    """

    aiohttp_client: Optional[aiohttp.ClientSession] = None
    _loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    async def get_aiohttp_client(cls) -> aiohttp.ClientSession:
        """Dapatkan ClientSession aktif (membuat jika belum ada/tertutup/
            loop berubah).

        Returns:
            aiohttp.ClientSession: Sesi aktif yang bisa digunakan untuk request.
        """
        loop = asyncio.get_running_loop()
        if (
            cls.aiohttp_client is None
            or cls.aiohttp_client.closed
            or cls._loop is not loop
        ):
            if cls.aiohttp_client and not cls.aiohttp_client.closed:
                try:  # noqa: SIM105
                    await cls.aiohttp_client.close()
                except Exception:
                    pass
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(limit=100, enable_cleanup_closed=True)
            cls.aiohttp_client = aiohttp.ClientSession(
                timeout=timeout, connector=connector, trust_env=True
            )
            cls._loop = loop
        return cls.aiohttp_client

    @classmethod
    async def aclose(cls) -> None:
        """Tutup ClientSession aktif (jika ada) dan reset state singleton."""
        if cls.aiohttp_client and not cls.aiohttp_client.closed:
            await cls.aiohttp_client.close()
        cls.aiohttp_client = None
        cls._loop = None

    @classmethod
    async def close_aiohttp_client(cls) -> None:
        """Alias penutupan ClientSession tanpa mereset informasi loop."""
        if cls.aiohttp_client:
            await cls.aiohttp_client.close()
            cls.aiohttp_client = None

    @classmethod
    async def request(
        cls,
        method: str,
        url: str,
        **kwargs: Unpack[aiohttp.client._RequestOptions],
    ) -> Any:
        """Kirim HTTP request menggunakan ClientSession singleton.

        Args:
            method: Metode HTTP (GET, POST, PUT, DELETE, dll.).
            url: URL tujuan.
            **kwargs: Opsi request aiohttp (headers, json, params, timeout, dll.).

        Returns:
            Any: Hasil parse JSON jika status 200; jika error, dict berisi pesan
                error.

        Catatan:
            - Saat status bukan 200, fungsi mengembalikan dict error sederhana.
            - Tangkap exception dan kembalikan dict {"ERROR": exc} untuk
                kesederhanaan.
        """
        client = await cls.get_aiohttp_client()

        try:
            async with client.request(method, url, **kwargs) as response:
                if response.status != 200:
                    return {"ERROR OCCURED" + str(await response.text())}

                json_result = await response.json()
        except Exception as e:
            return {"ERROR": e}

        return json_result


async def on_start_up() -> None:
    """Hook startup aplikasi: memastikan ClientSession dibuat."""
    await SingletonAiohttp.get_aiohttp_client()


async def on_shutdown() -> None:
    """Hook shutdown aplikasi: menutup ClientSession jika ada."""
    await SingletonAiohttp.aclose()
