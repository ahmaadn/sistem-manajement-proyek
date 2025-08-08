from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_utils.cbv import cbv

r = router = APIRouter(prefix="/auth", tags=["auth"])


@cbv(router)
class Authentication:
    @r.post("/login", status_code=status.HTTP_200_OK)
    async def login(self, credentials: OAuth2PasswordRequestForm = Depends()): ...

    @r.post("/validation", status_code=status.HTTP_202_ACCEPTED)
    async def validate_token(self, token: str): ...

    @r.post("/register", status_code=status.HTTP_200_OK)
    async def register(self): ...
