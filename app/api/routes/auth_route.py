from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_utils.cbv import cbv

from app.api.dependencies.authentication import unauthenticated_user_exception
from app.schemas.token import TokenAuth
from app.services.pegawai_service import PegawaiService

r = router = APIRouter(prefix="/auth", tags=["auth"])


@cbv(router)
class Authentication:
    pegawai_service: PegawaiService = Depends(PegawaiService)

    @r.post("/login", status_code=status.HTTP_200_OK)
    async def login(self, credentials: OAuth2PasswordRequestForm = Depends()):
        try:
            token = await self.pegawai_service.login(
                credentials.username, credentials.password
            )
            if not token:
                raise unauthenticated_user_exception()

            return TokenAuth(
                access_token=token["access_token"],
            )
        except Exception:
            raise unauthenticated_user_exception() from None
