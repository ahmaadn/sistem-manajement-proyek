from types import NoneType

from fastapi import APIRouter, Depends, Query, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.project import get_project_service
from app.api.dependencies.sessions import get_async_session
from app.api.dependencies.task import get_task_service
from app.api.dependencies.user import get_current_user
from app.db.models.task_model import ResourceType, Task
from app.schemas.task import (
    SimpleTaskResponse,
    SubTaskResponse,
    TaskCreate,
    TaskResponse,
)
from app.schemas.user import UserProfile
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.utils import exceptions

r = router = APIRouter(tags=["Task"])


@cbv(r)
class _Task:
    user: UserProfile = Depends(get_current_user)
    task_service: TaskService = Depends(get_task_service)
    project_service: ProjectService = Depends(get_project_service)
    session: AsyncSession = Depends(get_async_session)

    @r.get(
        "/projects/{project_id}/tasks",
        response_model=list[TaskResponse],
        status_code=status.HTTP_200_OK,
    )
    async def get_tasks(self, project_id: int):
        """Mendapatkan daftar tugas untuk proyek tertentu."""

        return await self.task_service.list(
            filters={"project_id": project_id, "parent_id": None},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(
                selectinload(Task.sub_tasks, recursion_depth=1)
            ),
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
    ):
        """Membuat tugas baru untuk proyek tertentu."""
        await self.project_service.get(payload.project_id)

        # handle display order None atau 0
        payload.display_order = await self.task_service.validate_display_order(
            payload.project_id, payload.display_order
        )

        task = await self.task_service.create(
            payload,
            extra_fields={
                "parent_id": parent_task_id,
                "created_by": self.user.id,
            },
        )
        return SimpleTaskResponse.model_validate(task)

    @r.get(
        "/tasks/{task_id}",
        response_model=SimpleTaskResponse,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Task detail retrieved successfully",
                "model": SimpleTaskResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Task not found",
                "model": exceptions.AppErrorResponse,
            },
        },
    )
    async def get_detail_task(self, project_id: int, task_id: int):
        """Mendapatkan detail tugas untuk proyek tertentu."""

        task = await self.task_service.get(task_id)
        return SimpleTaskResponse.model_validate(task)

    @r.get(
        "/tasks/{task_id}/subtasks",
        response_model=list[SubTaskResponse],
    )
    async def get_subtasks(self, task_id: int):
        """Mendapatkan daftar sub-tugas untuk tugas tertentu."""

        return await self.task_service.list(
            filters={"parent_id": task_id},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(selectinload(Task.sub_tasks)),
        )

    @r.delete(
        "/tasks/{task_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "task berhasil dihapus",
                "model": NoneType,
            }
        },
    )
    async def delete_task(self, task_id: int) -> NoneType:
        """Menghapus tugas tertentu."""

        task = await self.task_service.get(
            task_id, options=[selectinload(Task.sub_tasks)]
        )
        if not task:
            return

        await self.task_service.soft_delete(task_id)

        if task.resource_type == ResourceType.SECTION:
            tasks = []
            for sub_task in task.sub_tasks:
                sub_task.parent_id = None
                tasks.append(sub_task)

            self.session.add_all(tasks)
        else:
            # TODO: Implement logic for non-section tasks

            pass

        return
