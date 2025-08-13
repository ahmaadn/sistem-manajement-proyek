from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_utils.cbv import cbv

from app.api.dependencies.authentication import AuthHandler, auth_handler
from app.schemas.token import TokenAuth
from app.utils.exceptions import AppErrorResponse, UnauthorizedError

r = router = APIRouter(prefix="/auth", tags=["auth"])


@cbv(router)
class _Auth:
    @r.post(
        "/login",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Login Berhasil",
                "model": TokenAuth,
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Kredensial tidak valid",
                "model": AppErrorResponse,
            },
        },
    )
    async def login(
        self,
        credentials: OAuth2PasswordRequestForm = Depends(),
        authenticate: AuthHandler = Depends(auth_handler),
    ):
        try:
            token = await authenticate.login(
                username_or_email=credentials.username,
                password=credentials.password,
            )
            return TokenAuth(
                access_token=token["access_token"],
            )
        except UnauthorizedError as e:
            print("[INFO] Unauthorized access attempt")

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=e.dump(),
            ) from None
