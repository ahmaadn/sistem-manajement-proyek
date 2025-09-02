from types import NoneType

from fastapi import APIRouter, Body, Depends, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.services import get_task_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user, get_user_pm
from app.db.models.task_model import StatusTask
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.task import (
    SimpleTaskResponse,
    TaskCreate,
    TaskDetailResponse,
    TaskUpdate,
)
from app.schemas.user import User
from app.services.task_service import TaskService
from app.utils import exceptions

r = router = APIRouter(tags=["Task"])


@cbv(r)
class _Task:
    user: User = Depends(get_current_user)
    task_service: TaskService = Depends(get_task_service)
    session: AsyncSession = Depends(get_async_session)
    uow: UnitOfWork = Depends(get_uow)

    @r.post(
        "/milestones/{milestone_id}/tasks",
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
    async def create_task(self, milestone_id: int, payload: TaskCreate):
        """
        Membuat tugas baru untuk proyek tertentu.
        - Akses hanya bisa dilakukan oleh project manager (Owner).
        - Masih bisa menambahkan task walaupun project telah di delete

        **Akses** : Owner Project
        """
        # display_order handled in service
        async with self.uow:
            task = await self.task_service.create_task(
                user=self.user, milestone_id=milestone_id, payload=payload
            )
            await self.uow.commit()
        return task

    @r.post(
        "/tasks/{task_id}/subtasks",
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
    async def create_subtask(self, task_id: int, payload: TaskCreate):
        """
        Membuat tugas baru untuk proyek tertentu.
        - Akses hanya bisa dilakukan oleh project manager (Owner).
        - Masih bisa menambahkan task walaupun project telah di delete

        **Akses** : Owner Project
        """
        # display_order handled in service
        async with self.uow:
            task = await self.task_service.create_subtask(
                user=self.user, task_id=task_id, payload=payload
            )
            await self.uow.commit()
        return task

    @r.get(
        "/tasks/{task_id}",
        response_model=TaskDetailResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_403_FORBIDDEN: {
                "description": "User tidak memiliki akses ke proyek ini",
                "model": exceptions.AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Task atau project tidak ditemukan",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_detail_task(self, task_id: int):
        """
        Mendapatkan detail tugas untuk proyek tertentu.

        **Akses** : Semua Anggota Project, Admin
        """
        return await self.task_service.get_detail_task(
            user=self.user, task_id=task_id
        )

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

        async with self.uow:
            await self.task_service.delete_task(user=self.user, task_id=task_id)
            await self.uow.commit()

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

        **Akses** : Owner Project
        """

        async with self.uow:
            updated = await self.task_service.update_task(
                user=self.user, task_id=task_id, payload=payload
            )
            await self.uow.commit()
        return updated

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


        **Akses** : Anggota Assigned (Anggota yang ditugaskan)
        """
        async with self.uow:
            updated = await self.task_service.change_status(
                task_id, new_status=status, actor_user_id=self.user.id
            )
            await self.uow.commit()
        return updated

    @r.get(
        "/users/me/tasks",
        response_model=list[SimpleTaskResponse],
        status_code=status.HTTP_200_OK,
    )
    async def get_user_tasks(self):
        """
        Mendapatkan daftar tugas yang ditugaskan kepada pengguna tertentu.

        **Akses** : Semua Anggota Project yang ditugaskan
        """
        return await self.task_service.list_user_tasks(user=self.user)
