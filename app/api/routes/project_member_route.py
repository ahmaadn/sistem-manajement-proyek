from types import NoneType

from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import get_project_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_user_service, permission_required
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.base import MessageSuccessSchema
from app.schemas.project_member import ProjectMemberAdd, ProjectMemberRoleUpdate
from app.schemas.user import User
from app.services.project_service import ProjectService
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(tags=["Project Members"])


@cbv(r)
class _Project:
    session: AsyncSession = Depends(get_async_session)
    user: User = Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
    uow: UnitOfWork = Depends(get_uow)
    project_service: ProjectService = Depends(get_project_service)
    user_service: UserService = Depends(get_user_service)

    @r.post(
        "/projects/{project_id}/members",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                "description": "Anggota berhasil ditambahkan ke proyek",
                "model": MessageSuccessSchema,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "User tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_406_NOT_ACCEPTABLE: {
                "description": "Anggota sudah terdaftar di proyek",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_406_NOT_ACCEPTABLE: {
                "description": (
                    "Anggota sudah terdaftar di proyek atau Peran tidak valid untuk "
                    "pengguna. admin hanya bisa menjadi owner dan member tidak "
                    "dapat diangkat menjadi owner."
                ),
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def add_member(self, project_id: int, payload: ProjectMemberAdd):
        """
        Menambahkan anggota ke proyek

        **Akses** : Project Manajer (Owner), Admin
        """
        # Ambil info user yang akan ditambahkan (tanpa logika bisnis di router)
        member_info = await self.user_service.get_user(user_id=payload.user_id)
        if not member_info:
            raise exceptions.UserNotFoundError

        async with self.uow:
            await self.project_service.assign_project_member(
                project_id, self.user, member_info, payload.role
            )
            await self.uow.commit()

        return {"message": "Anggota berhasil ditambahkan ke proyek"}

    @r.delete(
        "/projects/{project_id}/members/{user_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "Anggota berhasil dihapus dari proyek",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Anggota tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "Tidak dapat menghapus creator project",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_406_NOT_ACCEPTABLE: {
                "description": "Tidak dapat menghapus anggota proyek",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def remove_member(self, project_id: int, user_id: int) -> NoneType:
        """
        Menghapus anggota dari proyek
        - tidak bisa menghapus diri sendiri
        - tidak bisa menghapus creator proyek

        **Akses** : Project Manajer (Owner), Admin
        """
        member_info = await self.user_service.get_user(user_id)
        if not member_info:
            raise exceptions.MemberNotFoundError

        async with self.uow:
            await self.project_service.remove_project_member(
                project_id, self.user, member_info
            )
            await self.uow.commit()

    @r.patch(
        "/projects/{project_id}/members/{user_id}/role",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "Peran anggota proyek berhasil diubah",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Anggota tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_406_NOT_ACCEPTABLE: {
                "description": "Peran tidak valid untuk pengguna",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def change_role_project_member(
        self, project_id: int, user_id: int, payload: ProjectMemberRoleUpdate
    ) -> NoneType:
        """
        Mengganti Role Project
        - Tidak dapat menganti role creator
        - Tidak dapat menggati role jika user saat ini

        **Akses** : Project Manajer (Owner), Admin (Owner)
        """
        member_info = await self.user_service.get_user(user_id)
        if not member_info:
            raise exceptions.MemberNotFoundError

        async with self.uow:
            await self.project_service.change_role_member_by_actor(
                project_id, self.user, member_info, payload.role
            )
            await self.uow.commit()
