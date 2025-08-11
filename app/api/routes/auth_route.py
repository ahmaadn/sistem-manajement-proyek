from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_utils.cbv import cbv

from app.schemas.token import TokenAuth
from app.services.pegawai_service import pegawai_service

r = router = APIRouter(prefix="/auth", tags=["auth"])


@cbv(router)
class Authentication:
    def __init__(self) -> None:
        self.pegawai_service = pegawai_service

    @r.post("/login", status_code=status.HTTP_200_OK)
    async def login(self, credentials: OAuth2PasswordRequestForm = Depends()):
        token = await self.pegawai_service.login(
            credentials.username, credentials.password
        )
        return TokenAuth(
            access_token=token["access_token"],
        )
