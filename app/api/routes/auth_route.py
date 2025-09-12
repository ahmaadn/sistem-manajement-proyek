from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_utils.cbv import cbv

from app.api.dependencies.authentication import AuthHandler, auth_handler
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_user_service
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.token import AuthToken
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(prefix="/auth", tags=["auth"])


@cbv(router)
class _Auth:
    @r.post(
        "/login",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Login Berhasil",
                "model": AuthToken,
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Kredensial tidak valid",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def login(
        self,
        credentials: OAuth2PasswordRequestForm = Depends(),
        authenticate: AuthHandler = Depends(auth_handler),
        user_service: UserService = Depends(get_user_service),
        uow: UnitOfWork = Depends(get_uow),
    ):
        token, user_info = await authenticate.login(
            username_or_email=credentials.username,
            password=credentials.password,
        )
        async with uow:
            await user_service.assign_role_to_user(user_id=user_info.id, user=user_info)
            await uow.commit()

        return AuthToken(
            access_token=token["access_token"],
        )
