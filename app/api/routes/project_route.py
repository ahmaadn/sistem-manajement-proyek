from types import NoneType

from fastapi import APIRouter, Body, Depends, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.project import get_project_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.task import get_task_service
from app.api.dependencies.user import get_current_user, get_user_service
from app.db.models.project_member_model import RoleProject
from app.db.models.project_model import Project
from app.db.models.role_model import Role
from app.db.models.task_model import ResourceType, StatusTask
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectStatsResponse,
    ProjectUpdate,
)
from app.schemas.user import UserProfile
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(tags=["Projects"])


@cbv(r)
class _Project:
    session: AsyncSession = Depends(get_async_session)
    user: UserProfile = Depends(get_current_user)
    project_service: ProjectService = Depends(get_project_service)

    @r.post(
        "/projects",
        status_code=status.HTTP_201_CREATED,
        response_model=ProjectResponse,
        responses={
            status.HTTP_201_CREATED: {
                "description": "proyek berhasil dibuat",
                "model": ProjectResponse,
            }
        },
    )
    async def create_project(self, project: ProjectCreate):
        """membuat proyek baru"""

        project_item = await self.project_service.create(
            project, extra_fields={"created_by": self.user.id}
        )
        return self._cast_project_to_response(project_item)

    @r.get(
        "/projects/{project_id}",
        response_model=ProjectDetailResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            }
        },
    )
    async def get_project(
        self,
        project_id: int,
        task_service: TaskService = Depends(get_task_service),
        user_service: UserService = Depends(get_user_service),
    ):
        """mengambil detail proyek"""
        project = await self.project_service.get(
            project_id,
            options=[selectinload(Project.members)],
        )
        if not project:
            raise exceptions.ProjectNotFoundError

        tasks = await task_service.list(
            filters={"project_id": project_id, "resource_type": ResourceType.TASK},
        )

        milestones = await task_service.list(
            filters={
                "project_id": project_id,
                "resource_type": ResourceType.MILESTONE,
            },
        )

        total_tasks = len(tasks)
        total_completed_tasks = sum(
            1 for t in tasks if t.status == StatusTask.COMPLETED
        )
        total_milestones = len(milestones)
        task_milestones_completed = sum(
            1 for m in milestones if m.status == StatusTask.COMPLETED
        )

        # get members
        members = []
        for member in project.members:
            user = await user_service.get(member.user_id)
            if user:
                members.append(
                    ProjectMemberResponse(
                        user_id=user.id,
                        name=user.name,
                        email=user.email,
                        project_role=member.role,
                    )
                )

        return ProjectDetailResponse(
            id=project.id,
            title=project.title,
            description=project.description,
            start_date=project.start_date,
            end_date=project.end_date,
            status=project.status,
            owner_id=project.created_by,
            members=members,
            stats=ProjectStatsResponse(
                total_tasks=total_tasks,
                total_completed_tasks=total_completed_tasks,
                total_milestones=total_milestones,
                task_milestones_completed=task_milestones_completed,
            ),
        )

    @r.put(
        "/projects/{project_id}",
        status_code=status.HTTP_200_OK,
        response_model=ProjectResponse,
        responses={
            status.HTTP_200_OK: {
                "description": "Proyek berhasil diperbarui",
                "model": ProjectResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def update_proyek(self, project_id: int, proyek: ProjectUpdate):
        """memperbarui proyek"""
        proyek_item = await self.project_service.update(project_id, proyek)
        return self._cast_project_to_response(proyek_item)

    @r.delete(
        "/projects/{project_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "Proyek berhasil dihapus",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def delete_proyek(self, project_id: int) -> NoneType:
        """menghapus proyek"""
        await self.project_service.soft_delete(project_id)

    @r.post(
        "/projects/{project_id}/members",
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                "description": "Anggota berhasil ditambahkan ke proyek",
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
                    "Anggota sudah terdaftar di proyek atau Peran tidak valid untuk pengguna. "
                    "admin hanya bisa menjadi owner dan member tidak dapat diangkat menjadi owner."
                ),
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def add_member(
        self,
        project_id: int,
        user_id: int = Body(..., embed=True),
        role: RoleProject = Body(default=RoleProject.CONTRIBUTOR, embed=True),
        member: UserService = Depends(get_user_service),
    ):
        """menambahkan anggota ke proyek"""

        # validasi project id
        project_info = await self.project_service.get(project_id)
        if not project_info:
            raise exceptions.ProjectNotFoundError

        member_info = await member.get(user_id)
        if not member_info:
            raise exceptions.UserNotFoundError

        # admin tidak dapat diangkat selain menjadi owner
        if (
            member_info.role in (Role.ADMIN, Role.MANAGER)
            and role != RoleProject.OWNER
        ):
            raise exceptions.InvalidRoleAssignmentError(
                "admin dan manager hanya bisa menjadi owner."
            )

        # Member tidak dapat diangkat menjadi owner
        if member_info.role == Role.TEAM_MEMBER and role == RoleProject.OWNER:
            raise exceptions.InvalidRoleAssignmentError(
                "Member tidak dapat diangkat menjadi owner."
            )

        await self.project_service.add_member(project_id, user_id, role)

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
            status.HTTP_406_NOT_ACCEPTABLE: {
                "description": "Tidak dapat menghapus anggota proyek",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def remove_member(self, user_id: int, project_id: int) -> NoneType:
        """menghapus anggota dari proyek"""

        # validasi project id
        project_info = await self.project_service.get(project_id)
        if not project_info:
            raise exceptions.ProjectNotFoundError

        member_info = await self.project_service.get_member(project_id, user_id)
        if not member_info:
            raise exceptions.MemberNotFoundError

        # tidak bisa menghapus diri sendiri
        if member_info.user_id == self.user.id:
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
        self,
        project_id: int,
        user_id: int,
        role: RoleProject = Body(..., embed=True),
        user_service: UserService = Depends(get_user_service),
    ):
        member_info = await user_service.get(user_id)
        if not member_info:
            raise exceptions.MemberNotFoundError

        await self.project_service.change_role_member(project_id, member_info, role)

    def _cast_project_to_response(self, proyek: Project) -> ProjectResponse:
        """
        Mengonversi objek Proyek menjadi objek ProjectResponse.

        Args:
            proyek (Proyek): Objek proyek yang akan dikonversi.

        Returns:
            ProjectResponse: Objek response yang berisi data proyek.
        """

        return ProjectResponse(
            id=proyek.id,
            title=proyek.title,
            description=proyek.description,
            status=proyek.status,
            owner_id=proyek.created_by,
            start_date=proyek.start_date,
            end_date=proyek.end_date,
        )
