from fastapi import APIRouter, Depends
from fastapi_utils.cbv import cbv

from app.api.dependencies.user import get_current_user, get_user_admin
from app.schemas.user import UserProfile
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

r = router = APIRouter(tags=["users"])


@cbv(router)
class User:
    @r.get("/users/me")
    async def me(self, user: UserProfile = Depends(get_current_user)):
        return user

    @r.get("/users/{user_id}")
    async def get_user_info(
        self,
        user_id: int,
        admin: UserProfile = Depends(get_user_admin),
        user_service: PegawaiService = Depends(PegawaiService),
    ):
        """
        Get user info by user_id without access_token.
        """
        user_info = await user_service.get_user_info(user_id)
        if not user_info:
            raise exceptions.UserNotFoundError
        return user_info
