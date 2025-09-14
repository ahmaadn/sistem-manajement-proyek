import logging

from fastapi_mail import ConnectionConfig
from pydantic import SecretStr, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "Template FastApi Backend"
    VERSION_API: int = 1

    BASE_API_PEGAWAI: str

    DB_DRIVER: str
    DB_SERVER: str
    DB_PORT: int
    DB_DATABASE: str
    DB_USERNAME: str
    DB_PASSWORD: str

    @computed_field
    @property
    def db_url(self) -> MultiHostUrl:
        return MultiHostUrl.build(
            scheme=self.DB_DRIVER,
            username=self.DB_USERNAME,
            password=self.DB_PASSWORD,
            host=self.DB_SERVER,
            port=self.DB_PORT,
            path=self.DB_DATABASE,
        )  # type: ignore

    # Mail configuration
    MAIL_SERVER: str = "smtp.gmail.com"
    MAIL_PORT: int = 587
    MAIL_USERNAME: str = ""
    MAIL_FROM: str = ""
    MAIL_PASSWORD: SecretStr = ""  # type: ignore
    MAIL_SSL_TLS: bool = True

    @computed_field
    @property
    def mail_config(self) -> ConnectionConfig:
        return ConnectionConfig(
            MAIL_USERNAME=self.MAIL_USERNAME,
            MAIL_PASSWORD=self.MAIL_PASSWORD,
            MAIL_FROM=self.MAIL_FROM,
            MAIL_PORT=self.MAIL_PORT,
            MAIL_SERVER=self.MAIL_SERVER,
            MAIL_STARTTLS=True,
            MAIL_SSL_TLS=self.MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True,
        )

    @computed_field
    @property
    def version_url(self) -> str:
        return f"/v{self.VERSION_API}"

    # CLOUD STORAGE
    CLOUDINARY_CLOUD_NAME: str = ""
    CLOUDINARY_API_KEY: str = ""
    CLOUDINARY_API_SECRET: str = ""

    # REALTIME DRIVERS
    # contoh isi : websocket,sse,pusher
    # konfigurasi punjer ada di app/core/config/pusher.py
    REALTIME_DRIVERS: str = "websocket,sse,pusher"

    _ALLOWED = {"websocket", "sse", "pusher"}

    def get_enabled_drivers(self) -> set[str]:
        """
        Baca env REALTIME_DRIVERS, default: "websocket,sse"
        Contoh: REALTIME_DRIVERS=pusher  -> hanya Pusher
                REALTIME_DRIVERS=websocket -> hanya WS
        """
        items = {
            x.strip().lower() for x in self.REALTIME_DRIVERS.split(",") if x.strip()
        }
        enabled = {x for x in items if x in self._ALLOWED}

        # Beritahu jika Pusher diaktifkan tapi setting yang diperlukan tidak lengkap
        if "pusher" in enabled:
            try:
                from app.core.config.pusher import get_pusher_config

                cfg = get_pusher_config()
                if not cfg.cek_valid():
                    enabled.remove("pusher")
            except Exception:
                logger = logging.getLogger(__name__)
                logger.warning(
                    (
                        "REALTIME_DRIVERS includes 'pusher' but PusherConfig "
                        "is not available"
                    )
                )
                enabled.remove("pusher")

        return enabled


def _singleton(cls):
    _instances = {}

    def warp():
        if cls not in _instances:
            _instances[cls] = cls()
        return _instances[cls]

    return warp


Settings = _singleton(Settings)  # type: ignore


def get_settings() -> "Settings":
    """Mendapatkan setting

    Returns
    -------
        Settings: instance settings

    """
    return Settings()  # type: ignore


settings = get_settings()

if __name__ == "__main__":
    print(settings)
