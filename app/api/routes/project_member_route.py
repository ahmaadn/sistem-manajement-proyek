from types import NoneType

from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import get_project_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.user import get_user_service, permission_required
from app.db.models.project_member_model import RoleProject
from app.db.models.role_model import Role
from app.schemas.base import MessageSuccessSchema
from app.schemas.project_member import AddMemberProject, ChangeRoleProject
from app.schemas.user import User
from app.services.project_service import ProjectService
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(tags=["Project Members"])


@cbv(r)
class _Project:
    session: AsyncSession = Depends(get_async_session)
    user: User = Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
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
    async def add_member(self, project_id: int, payload: AddMemberProject):
        """
        Menambahkan anggota ke proyek

        **Akses** : Project Manajer (Owner), Admin (Owner)
        """

        # Mendapatkan project berdasarkan owner
        await self.project_service.get_project_by_owner(self.user.id, project_id)

        # validasi member yang akan dimasukkan
        member_info = await self.user_service.get(user_id=payload.user_id)
        if not member_info:
            raise exceptions.UserNotFoundError

        # admin tidak dapat diangkat selain menjadi owner
        if (
            member_info.role in (Role.ADMIN, Role.PROJECT_MANAGER)
            and payload.role != RoleProject.OWNER
        ):
            raise exceptions.InvalidRoleAssignmentError(
                "admin dan manager hanya bisa menjadi owner."
            )

        # Member tidak dapat diangkat menjadi owner
        if (
            member_info.role == Role.TEAM_MEMBER
            and payload.role == RoleProject.OWNER
        ):
            raise exceptions.InvalidRoleAssignmentError(
                "Member tidak dapat diangkat menjadi owner."
            )

        await self.project_service.add_member(
            project_id, payload.user_id, payload.role
        )

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
    async def remove_member(self, user_id: int, project_id: int) -> NoneType:
        """
        Menghapus anggota dari proyek
        - tidak bisa menghapus diri sendiri
        - tidak bisa menghapus creator proyek

        **Akses** : Project Manajer (Owner), Admin (Owner)
        """

        # validasi project id
        project = await self.project_service.get_project_by_owner(
            self.user.id, project_id
        )

        # validasi member yang akan dihapus
        member_info = await self.project_service.get_member(project_id, user_id)
        if not member_info:
            raise exceptions.MemberNotFoundError

        # tidak bisa menghapus diri sendiri
        # tidak bisa menghapus creator proyek
        if member_info.user_id in (self.user.id, project.created_by):
            raise exceptions.CannotRemoveMemberError

        await self.project_service.remove_member(project_id, user_id)

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
        self, project_id: int, user_id: int, payload: ChangeRoleProject
    ) -> NoneType:
        """
        Mengganti Role Project
        - Tidak dapat menganti role creator
        - Tidak dapat menggati role jika user saat ini

        **Akses** : Project Manajer (Owner), Admin (Owner)
        """
        project = await self.project_service.get_project_by_owner(
            self.user.id, project_id
        )

        # Tidak dapat mengganti role creator
        if user_id in (project.created_by, self.user.id):
            raise exceptions.CannotChangeRoleError

        member_info = await self.user_service.get(user_id)
        if not member_info:
            raise exceptions.MemberNotFoundError

        await self.project_service.change_role_member(
            project_id, member_info, payload.role
        )
