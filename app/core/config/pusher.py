from __future__ import annotations

import logging

from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class PusherConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    # Core Pusher credentials
    PUSHER_APP_ID: str = ""

    # Kunci publik Pusher
    PUSHER_KEY: str = ""

    # Token rahasia Pusher
    PUSHER_SECRET: str = ""

    # Cluster Pusher, misal: ap1, eu, us2, dll
    PUSHER_CLUSTER: str = "ap1"

    # Gunakan koneksi SSL/TLS
    PUSHER_SSL: bool = True

    # Enable/disable Ekspose endpoint test sederhana
    PUSHER_TEST_ENABLE: bool = True

    # Kustom URL path for the test page; must include `{user_id}` path param
    PUSHER_TEST_PATH: str = "/test/pusher/user/{user_id}"

    # Lokasi template kustom; gunakan default jika tidak diubah
    PUSHER_TEMPLATE_DIR: str = "app/templates"

    # Nama file template untuk halaman test
    PUSHER_TEMPLATE_NAME: str = "pusher_test_notify.html"

    def cek_valid(self) -> bool:
        missing: list[str] = []
        if not self.PUSHER_APP_ID:
            missing.append("PUSHER_APP_ID")
        if not self.PUSHER_KEY:
            missing.append("PUSHER_KEY")
        if not self.PUSHER_SECRET:
            missing.append("PUSHER_SECRET")
        if not self.PUSHER_CLUSTER:
            missing.append("PUSHER_CLUSTER")

        if missing:
            logger.warning(
                ("REALTIME_DRIVERS includes 'pusher' but missing settings: %s"),
                ", ".join(missing),
            )

        return len(missing) == 0


def _singleton(cls):
    _instances = {}

    def warp():
        if cls not in _instances:
            _instances[cls] = cls()
        return _instances[cls]

    return warp


PusherConfig = _singleton(PusherConfig)  # type: ignore


def get_pusher_config() -> "PusherConfig":
    return PusherConfig()  # type: ignore
