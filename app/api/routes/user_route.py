from fastapi import APIRouter, Depends, Query, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_project_service
from app.api.dependencies.task import get_task_service
from app.api.dependencies.user import (
    get_current_user,
    get_user_admin,
    get_user_service,
)
from app.schemas.pagination import SimplePaginationSchema
from app.schemas.user import User, UserDetail
from app.services.pegawai_service import PegawaiService
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["users"])


@cbv(router)
class _User:
    user_service: UserService = Depends(get_user_service)
    project_service: ProjectService = Depends(get_project_service)
    task_service: TaskService = Depends(get_task_service)

    @r.get(
        "/users/me",
        response_model=UserDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Pengguna tidak ditemukan",
                "model": UserDetail,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def me(
        self,
        user: User = Depends(get_current_user),
    ) -> UserDetail:
        """
        Mengambil Detail user
        """
        return await self.user_service.get_user_detail(
            user_data=user,
            project_service=self.project_service,
            task_service=self.task_service,
        )

    @r.get(
        "/users/{user_id}",
        response_model=UserDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Pengguna tidak ditemukan",
                "model": UserDetail,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def get_user_info(
        self,
        user_id: int,
        admin: User = Depends(get_user_admin),
        user_service: PegawaiService = Depends(PegawaiService),
    ) -> UserDetail:
        """
        Get user info by user_id without access_token.
        """

        return await self.user_service.get_user_detail(
            user_id=user_id,
            project_service=self.project_service,
            task_service=self.task_service,
        )

    @r.get("/users", response_model=SimplePaginationSchema[User])
    async def list_users(
        self,
        page: int = Query(default=1, ge=1),
        per_page: int = Query(default=10, ge=1),
    ) -> SimplePaginationSchema[User]:
        """
        List users with pagination.
        """
        users = await self.user_service.list_user()
        return SimplePaginationSchema[User](
            count=len(users),
            items=users,
        )
