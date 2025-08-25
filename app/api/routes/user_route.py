from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_project_service, get_task_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import (
    get_current_user,
    get_user_admin,
    get_user_service,
    permission_required,
)
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.pagination import SimplePaginationSchema
from app.schemas.user import User, UserDetail
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
    uow: UnitOfWork = Depends(get_uow)  # NEW

    @r.get(
        "/users/me",
        response_model=UserDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {"description": "OK", "model": UserDetail},
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def me(self, user: User = Depends(get_current_user)) -> UserDetail:
        """Mendapatkan detail informasi dari user saat ini

        **Akses**: Semua User
        """
        detail = await self.user_service.get_user_detail(
            user_data=user,
            project_service=self.project_service,
            task_service=self.task_service,
        )
        await self.uow.commit()  # commit jika ada role baru dibuat
        return detail

    @r.get(
        "/users/{user_id}",
        response_model=UserDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {"description": "OK", "model": UserDetail},
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Tidak punyak akses",
                "model": AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
        dependencies=[
            Depends(permission_required([Role.ADMIN, Role.PROJECT_MANAGER]))
        ],
    )
    async def get_user_info(
        self,
        user_id: int,
    ) -> UserDetail:
        """Mendapatkan detail user. hanyaa bisa di akses oleh admin dan project
            manajer

        **Akses** : Admin, Project Manajer
        """
        detail = await self.user_service.get_user_detail(
            user_id=user_id,
            project_service=self.project_service,
            task_service=self.task_service,
        )
        await self.uow.commit()
        return detail

    @r.get(
        "/users",
        response_model=SimplePaginationSchema[User],
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "OK",
                "model": SimplePaginationSchema[User],
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Tidak punyak akses",
                "model": AppErrorResponse,
            },
        },
        dependencies=[
            Depends(permission_required([Role.ADMIN, Role.PROJECT_MANAGER]))
        ],
    )
    async def list_users(self) -> SimplePaginationSchema[User]:
        """Mendapatkan semua user

        **Akses**: Admin, Project Manajer
        """
        users = await self.user_service.list_user()
        await self.uow.commit()
        return SimplePaginationSchema[User](
            count=len(users),
            items=users,
        )

    @r.patch(
        "/users/{user_id}/role",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Peran pengguna berhasil diubah",
                "model": dict,
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Tidak punyak akses",
                "model": AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def change_role(
        self, user_id: int, new_role: Role, admin: User = Depends(get_user_admin)
    ):
        """Mengubah peran pengguna

        **Akses**: Admin
        """
        await self.user_service.change_user_role(
            actor=admin, user_id=user_id, new_role=new_role
        )
        await self.uow.commit()
        return {"message": "Peran pengguna berhasil diubah"}
