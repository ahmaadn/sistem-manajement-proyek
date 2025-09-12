import asyncio
from typing import Any, Optional, Unpack

import aiohttp

SIZE_POOL_AIOHTTP = 100


class SingletonAiohttp:
    aiohttp_client: Optional[aiohttp.ClientSession] = None
    _loop: asyncio.AbstractEventLoop | None = None

    @classmethod
    async def get_aiohttp_client(cls) -> aiohttp.ClientSession:
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
        if cls.aiohttp_client and not cls.aiohttp_client.closed:
            await cls.aiohttp_client.close()
        cls.aiohttp_client = None
        cls._loop = None

    @classmethod
    async def close_aiohttp_client(cls) -> None:
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
    await SingletonAiohttp.get_aiohttp_client()


async def on_shutdown() -> None:
    await SingletonAiohttp.close_aiohttp_client()
