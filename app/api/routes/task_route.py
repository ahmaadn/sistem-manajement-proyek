from types import NoneType

from fastapi import APIRouter, Body, Depends, Query, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.services import get_project_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.task import get_task_service
from app.api.dependencies.user import get_current_user, get_user_pm, get_user_service
from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.task_model import ResourceType, StatusTask, Task
from app.schemas.task import (
    SimpleTaskResponse,
    SubTaskResponse,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
)
from app.schemas.user import User
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(tags=["Task"])


@cbv(r)
class _Task:
    user: User = Depends(get_current_user)
    task_service: TaskService = Depends(get_task_service)
    project_service: ProjectService = Depends(get_project_service)
    session: AsyncSession = Depends(get_async_session)

    # Helper: pastikan user adalah member project
    async def _ensure_project_member(self, project_id: int) -> ProjectMember:
        try:
            return await self.project_service.get_member(project_id, self.user.id)
        except exceptions.MemberNotFoundError:
            raise exceptions.UserNotInProjectError from None

    async def _ensure_project_owner(self, project_id: int) -> ProjectMember:
        project_member = await self._ensure_project_member(project_id)
        if project_member.role != RoleProject.OWNER:
            raise exceptions.ForbiddenError
        return project_member

    @r.get(
        "/projects/{project_id}/tasks",
        response_model=list[TaskResponse],
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Daftar tugas berhasil diambil",
                "model": list[TaskResponse],
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "User tidak memiliki akses ke proyek ini",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_tasks(self, project_id: int):
        """
        Mendapatkan daftar tugas untuk proyek tertentu.
        - Hanya user yang terdaftar sebagai anggota proyek yang dapat mengakses
            tugas.

        **Akses** : Anggota Proyek (Member, Project Manager, Admin)
        """

        # pastikan user adalah member project
        await self._ensure_project_member(project_id)

        return await self.task_service.list(
            filters={"project_id": project_id, "parent_id": None},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(
                selectinload(Task.sub_tasks, recursion_depth=1)
            ),
        )

    @r.get(
        "/projects/{project_id}/tasks/{task_id}/subtasks",
        status_code=status.HTTP_200_OK,
        response_model=list[SubTaskResponse],
        responses={
            status.HTTP_200_OK: {
                "description": "Daftar sub-tugas berhasil diambil",
                "model": list[SubTaskResponse],
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "User tidak memiliki akses ke proyek ini",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_subtasks(self, project_id: int, task_id: int):
        """
        Mendapatkan daftar sub-tugas untuk tugas tertentu.

        **Akses** : Semua Anggota Project
        """

        # pastikan user adalah member project
        await self._ensure_project_member(project_id)

        return await self.task_service.list(
            filters={"parent_id": task_id},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(selectinload(Task.sub_tasks)),
        )

    @r.post(
        "/tasks",
        response_model=SimpleTaskResponse,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_201_CREATED: {
                "description": "Task berhasil dibuat",
                "model": SimpleTaskResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Project tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def create_task(
        self,
        payload: TaskCreate,
        parent_task_id: int | None = Query(
            default=None, description="ID tugas induk jika ada"
        ),
        user: User = Depends(get_user_pm),
    ):
        """
        Membuat tugas baru untuk proyek tertentu.
        - Akses hanya bisa dilakukan oleh project manager (Owner).

        **Akses** : Project Manager (Owner)
        """

        # pastikan yang akses router adalah project manajer (Owner)
        await self._ensure_project_owner(payload.project_id)

        # handle display order None atau 0
        payload.display_order = await self.task_service.validate_display_order(
            payload.project_id, payload.display_order
        )

        return await self.task_service.create(
            payload,
            extra_fields={
                "parent_id": parent_task_id,
                "created_by": self.user.id,
            },
        )

    @r.get(
        "/tasks/{task_id}",
        response_model=SimpleTaskResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Task detail retrieved successfully",
                "model": SimpleTaskResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "User tidak memiliki akses ke proyek ini",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Task not found",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_detail_task(self, task_id: int):
        """
        Mendapatkan detail tugas untuk proyek tertentu.

        **Akses** : Semua Anggota Project
        """

        task = await self.task_service.get(task_id)
        assert task is not None

        # pastikan user adalah member project
        await self._ensure_project_member(task.project_id)

        return task

    @r.delete(
        "/tasks/{task_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "task berhasil dihapus",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "task tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def delete_task(
        self, task_id: int, user: User = Depends(get_user_pm)
    ) -> NoneType:
        """
        Menghapus tugas tertentu. hanya bisa dilakukan oleh owner

        **Akses** : Project Manager (Owner)
        """

        # Get task
        task = await self.task_service.get(
            task_id, options=[selectinload(Task.sub_tasks)]
        )
        assert task is not None  # Sudah di handle di get

        # pastikan yang akses router adalah project manajer (Owner)
        await self._ensure_project_owner(task.project_id)

        # Delete task
        await self.task_service.soft_delete(task_id)

        if task.resource_type == ResourceType.SECTION:
            tasks = []
            for sub_task in task.sub_tasks:
                sub_task.parent_id = None
                tasks.append(sub_task)

            self.session.add_all(tasks)
            await self.session.commit()
        else:
            # TODO: Implement logic for non-section tasks
            # hapus semua task berkaitan
            for sub_task in task.sub_tasks:
                await self.task_service.soft_delete(sub_task.id)

    @r.put(
        "/tasks/{task_id}",
        response_model=SimpleTaskResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Task berhasil diupdate",
                "model": SimpleTaskResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Task tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def update_task(
        self, task_id: int, payload: TaskUpdate, user: User = Depends(get_user_pm)
    ):
        """Mengupdate tugas tertentu.

        **Akses** : Project Manager (Owner)
        """

        # Mendapatkan task
        task = await self.task_service.get(task_id)
        assert task is not None

        # Pastikan user adalah pemilik proyek
        await self._ensure_project_owner(task.project_id)

        return await self.task_service.update(task, payload)

    @r.patch(
        "/tasks/{task_id}/status",
        response_model=SimpleTaskResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Status Task berhasil diupdate",
                "model": SimpleTaskResponse,
            },
            status.HTTP_403_FORBIDDEN: {
                "description": "Hanya assignee yang boleh mengubah status task",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Task tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def update_task_status(
        self, task_id: int, status: StatusTask = Body(..., embed=True)
    ):
        """
        Mengupdate status tugas tertentu.
        - Bisa digunakan untuk checkbox
        - Untuk Owner bisa menggunakan endpoint **PUT /v1/tasks/{task_id}**


        **Akses** : Anggota Assigned
        """

        task = await self.task_service.get(
            task_id, options=[selectinload(Task.assignees)]
        )
        assert task is not None

        # Hanya user yang ditugaskan (assignee) yang boleh mengubah status
        if not any(ass.user_id == self.user.id for ass in task.assignees):
            raise exceptions.ForbiddenError

        return await self.task_service.update(task, {"status": status})

    @r.post("/tasks/{task_id}/assign", status_code=status.HTTP_201_CREATED)
    async def assign_task(
        self,
        task_id: int,
        user_id: int = Body(..., embed=True),
        user_service: UserService = Depends(get_user_service),
    ) -> NoneType:
        """
        Menugaskan pengguna untuk tugas tertentu.

        **Akses** : Project Manager (Owner)
        """

        user = await user_service.get_user(user_id)
        assert user is not None

        task = await self.task_service.get(task_id)
        assert task is not None

        # Pastikan user adalah pemilik proyek
        await self._ensure_project_owner(task.project_id)

        await self.task_service.assign_user(task, user)
