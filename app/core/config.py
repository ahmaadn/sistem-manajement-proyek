from fastapi_mail import ConnectionConfig
from pydantic import SecretStr, computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    PROJECT_NAME: str = "Template FastApi Backend"
    VERSION_API: int = 1

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
