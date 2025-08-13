from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.user import get_current_user, get_user_admin
from app.schemas.user import UserProfile
from app.services.pegawai_service import PegawaiService
from app.utils.common import ErrorCode

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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": ErrorCode.USER_NOT_FOUND,
                    "message": "User tidak ada",
                },
            )
        return user_info
