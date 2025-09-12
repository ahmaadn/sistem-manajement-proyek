import logging
from time import perf_counter
from typing import Any

from fastapi import Request
from httpx import AsyncClient

from app.core.config.api_pegawai import PegawaiApiUrls
from app.middleware.request import request_object
from app.utils.aiohttp_client import SingletonAiohttp

logger = logging.getLogger(__name__)


def _get_bearer_from_ctx(req: Request) -> dict:
    """Ambil header Authorization Bearer dari request aktif.

    Jika header tidak diawali 'Bearer ', ia akan ditambahkan secara otomatis.

    Args:
        req: Objek request yang memiliki atribut headers.

    Returns:
        Dict header Authorization jika tersedia, atau dict kosong jika tidak ada.
    """
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth:
        return {}

    if not str(auth).lower().startswith("bearer "):
        auth = f"Bearer {auth}"

    return {"Authorization": auth}


def _auth_headers(req: Request, token: str | None) -> dict[str, str]:
    """Bangun header untuk permintaan HTTP dengan Accept JSON.

    Args:
        req: Objek request aktif (untuk fallback Authorization).
        token: Token Bearer eksplisit. Jika diberikan, digunakan sebagai prioritas.

    Returns:
        Dict header yang berisi Authorization (jika ada) dan Accept.
    """
    if token:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    return {**_get_bearer_from_ctx(req), "Accept": "application/json"}


class PegawaiApiClient:
    @staticmethod
    async def _request(
        method: str,
        url: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ):
        """Wrapper generik untuk mengirim request HTTP.

        Args:
            method (str): Metode HTTP (GET, POST, dst.).
            url (str): URL absolut endpoint.
            json (Any, optional): Payload JSON. Defaults to None.
            headers (dict[str, str] | None, optional): Header tambahan. Defaults
                to None.

        Raises:
            RuntimeError: Jika request.state.client tidak tersedia.
            Exception: Jika permintaan HTTP gagal (dilempar ulang setelah logging).

        Returns:
            _type_: Objek response dari client HTTP yang digunakan.
        """

        # dapatkan request aktif dari context var
        request = request_object.get()

        # dapatkan client HTTP dari request.state, client menggunakan
        # httpx.AsyncClient
        httpx_client: AsyncClient | None = getattr(request.state, "client", None)

        start = perf_counter()
        try:
            if httpx_client is not None:
                resp = await httpx_client.request(
                    method, url, json=json, headers=headers
                )
            else:
                # dikarenakan di hosting di serverles lifespan/startup
                # kadang tidak konsisten. Jika request.state.client tidak tersedia,
                # fallback ke client httpx.AsyncClient temporer.
                async with AsyncClient(http2=True) as tmp_client:
                    resp = await tmp_client.request(
                        method, url, json=json, headers=headers
                    )
                    # Pastikan body sudah dibaca sebelum client ditutup
                    await resp.aread()

            logger.debug(
                "%s %s -> %s in %.2f ms",
                method.upper(),
                url,
                resp.status_code,
                (perf_counter() - start) * 1000,
            )
            return resp
        except Exception:
            logger.exception("HTTP %s %s failed", method.upper(), url)
            raise

    @staticmethod
    async def login(*, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Lakukan autentikasi dan ambil token akses.

        Args:
            payload (dict[str, Any]): Body login (mis. email dan password).

        Returns:
            dict[str, Any] | None: berisi 'access_token', 'user', dan 'user_id'
                jika sukses; None jika gagal/format tak sesuai.
        """
        try:
            # mengirim request login
            resp = await PegawaiApiClient._request(
                "POST",
                PegawaiApiUrls.LOGIN,
                json=payload,
                headers={"Accept": "application/json"},
            )

            # periksa status code
            if resp.status_code != 200:
                logger.warning(
                    "Login failed: %s - %s",
                    resp.status_code,
                    getattr(resp, "text", ""),
                )
                return None

            # ekstrak token dan info user dari response
            data = resp.json()
            raw_token = data.get("token")
            user = data.get("user") or {}

            # token format di laravel seperti ini num|token maka ambil bagian
            # setelah '|'
            token = (
                raw_token.split("|")[-1]
                if isinstance(raw_token, str) and "|" in raw_token
                else raw_token
            )
            user_id = user.get("id")

            if not token or user_id is None:
                logger.warning("Unexpected login payload: %s", data)
                return None

            return {"access_token": token, "user": user, "user_id": user_id}
        except Exception:
            logger.exception("Error during login request")
            return None

    @staticmethod
    async def validation_token(*, token: str | None = None) -> bool:
        """Validasi token Bearer ke layanan Pegawai.

        Args:
            token (str | None): Token Bearer eksplisit (opsional). Jika tidak ada,
                fallback ke header Authorization request. Default to None

        Returns:
            True jika valid (HTTP 200), False jika tidak valid atau terjadi error.
        """
        req = request_object.get()
        headers = _auth_headers(req, token)
        try:
            resp = await PegawaiApiClient._request(
                "POST", PegawaiApiUrls.VALIDATION, headers=headers
            )
            return resp.status_code == 200
        except Exception:
            logger.exception("Error during validation_token request")
            return False

    @staticmethod
    async def get_pegawai_me(*, token: str | None = None):
        """Ambil profil pegawai berdasarkan token saat ini.

        Args:
            token (str | None): Token Bearer eksplisit (opsional). Default to None.

        Returns:
            Objek/dict data pegawai jika sukses, else None.
        """
        req = request_object.get()
        headers = _auth_headers(req, token)
        try:
            resp = await PegawaiApiClient._request(
                "GET", PegawaiApiUrls.PEGAWAI_ME, headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.debug("response get_pegawai_me: %s", data)
                return data
            return None
        except Exception:
            logger.exception("Error during get_pegawai_me request")
            return None

    @staticmethod
    async def get_pegawai_detail(*, user_id: int, token: str | None = None):
        """Ambil detail pegawai berdasarkan user_id.

        Args:
            user_id (int): ID pengguna/pegawai.
            token (str | None): Token Bearer eksplisit (opsional). Default to None.

        Returns:
            Objek/dict detail pegawai jika sukses, else None.
        """
        req = request_object.get()
        headers = _auth_headers(req, token)
        try:
            resp = await PegawaiApiClient._request(
                "GET", PegawaiApiUrls.pegawai_detail(user_id), headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.debug("response get_pegawai_detail: %s", data)
                return data
            return None
        except Exception:
            logger.exception("Error during get_pegawai_detail request")
            return None

    @staticmethod
    async def get_list_pegawai(*, token: str | None = None):
        """Ambil daftar pegawai.

        Args:
            token (str | None): Token Bearer eksplisit (opsional). Default to None.

        Returns:
            List/array pegawai jika sukses, else None.
        """
        req = request_object.get()
        headers = _auth_headers(req, token)
        try:
            resp = await PegawaiApiClient._request(
                "GET", PegawaiApiUrls.PEGAWAI_LIST, headers=headers
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.debug("response get_list_pegawai: %s", data)
                return data
            return None
        except Exception:
            logger.exception("Error during get_list_pegawai request")
            return None

    @staticmethod
    async def get_bulk_pegawai(*, ids: list[int], token: str | None = None):
        """Ambil data pegawai secara bulk berdasarkan daftar ID.

        Args:
            ids (list[int]): Daftar ID pegawai.
            token (str | None): Token Bearer eksplisit (opsional). Default to None.

        Returns:
            List/array data pegawai jika sukses, else None.
        """
        req = request_object.get()
        headers = {**_auth_headers(req, token), "Content-Type": "application/json"}
        try:
            resp = await PegawaiApiClient._request(
                "POST",
                PegawaiApiUrls.PEGAWAI_BULK,
                json={"ids": ids},
                headers=headers,
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.debug("response get_bulk_pegawai: %s", data)
                return data
            return None
        except Exception:
            logger.exception("Error during get_bulk_pegawai request")
            return None


class PegawaiAiohttpClient:
    """Client HTTP berbasis aiohttp via SingletonAiohttp."""

    @staticmethod
    async def _request(
        method: str,
        url: str,
        *,
        json: Any = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, Any | None, str]:
        start = perf_counter()
        client = SingletonAiohttp.get_aiohttp_client()
        try:
            async with client.request(
                method, url, json=json, headers=headers
            ) as resp:
                status = resp.status
                text = await resp.text()
                data = None
                ct = resp.headers.get("Content-Type", "")
                if "application/json" in ct.lower():
                    try:
                        data = await resp.json()
                    except Exception:
                        data = None
                logger.debug(
                    "%s %s -> %s in %.2f ms",
                    method.upper(),
                    url,
                    status,
                    (perf_counter() - start) * 1000,
                )
                return status, data, text
        except Exception:
            logger.exception("HTTP %s %s failed (aiohttp)", method.upper(), url)
            raise

    @staticmethod
    async def login(*, payload: dict[str, Any]) -> dict[str, Any] | None:
        status, data, text = await PegawaiAiohttpClient._request(
            "POST",
            PegawaiApiUrls.LOGIN,
            json=payload,
            headers={"Accept": "application/json"},
        )
        if status != 200 or not isinstance(data, dict):
            logger.warning("Login failed: %s - %s", status, text)
            return None

        raw_token = data.get("token")
        user = data.get("user") or {}
        token = (
            raw_token.split("|")[-1]
            if isinstance(raw_token, str) and "|" in raw_token
            else raw_token
        )
        user_id = user.get("id")
        if not token or user_id is None:
            logger.warning("Unexpected login payload: %s", data)
            return None
        return {"access_token": token, "user": user, "user_id": user_id}

    @staticmethod
    async def validation_token(*, token: str | None = None) -> bool:
        req = request_object.get()
        headers = _auth_headers(req, token)
        status, _, _ = await PegawaiAiohttpClient._request(
            "POST", PegawaiApiUrls.VALIDATION, headers=headers
        )
        return status == 200

    @staticmethod
    async def get_pegawai_me(*, token: str | None = None):
        req = request_object.get()
        headers = _auth_headers(req, token)
        status, data, _ = await PegawaiAiohttpClient._request(
            "GET", PegawaiApiUrls.PEGAWAI_ME, headers=headers
        )
        return data if status == 200 else None

    @staticmethod
    async def get_pegawai_detail(*, user_id: int, token: str | None = None):
        req = request_object.get()
        headers = _auth_headers(req, token)
        status, data, _ = await PegawaiAiohttpClient._request(
            "GET", PegawaiApiUrls.pegawai_detail(user_id), headers=headers
        )
        return data if status == 200 else None

    @staticmethod
    async def get_list_pegawai(*, token: str | None = None):
        req = request_object.get()
        headers = _auth_headers(req, token)
        status, data, _ = await PegawaiAiohttpClient._request(
            "GET", PegawaiApiUrls.PEGAWAI_LIST, headers=headers
        )
        return data if status == 200 else None

    @staticmethod
    async def get_bulk_pegawai(*, ids: list[int], token: str | None = None):
        req = request_object.get()
        headers = {**_auth_headers(req, token), "Content-Type": "application/json"}
        status, data, _ = await PegawaiAiohttpClient._request(
            "POST",
            PegawaiApiUrls.PEGAWAI_BULK,
            json={"ids": ids},
            headers=headers,
        )
        return data if status == 200 else None
