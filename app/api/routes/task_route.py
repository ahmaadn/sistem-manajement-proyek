from fastapi import APIRouter, Depends, Path, Query
from fastapi_utils.cbv import cbv

from app.api.dependencies.project import get_project_service
from app.api.dependencies.task import get_task_service
from app.api.dependencies.user import get_current_user
from app.db.models.task_model import Task
from app.schemas.task import TaskCreate, TaskResponse
from app.schemas.user import UserProfile
from app.services.project_service import ProjectService
from app.services.task_service import TaskService

r = router = APIRouter(prefix="/project", tags=["Task", "Project"])


@cbv(r)
class _Task:
    user: UserProfile = Depends(get_current_user)
    task_service: TaskService = Depends(get_task_service)
    project_service: ProjectService = Depends(get_project_service)

    @r.get("/{project_id}/tasks", response_model=list[TaskResponse])
    async def get_tasks(self, project_id: int):
        """Mendapatkan daftar tugas untuk proyek tertentu."""

        tasks = await self.task_service.list(
            filters={"project_id": project_id}, order_by=Task.display_order
        )

        return tasks

    @r.post("/{project_id}/tasks")
    async def create_task(
        self,
        payload: TaskCreate,
        project_id: int = Path(default=..., description="ID proyek"),
        parent_task_id: int | None = Query(
            default=None, description="ID tugas induk jika ada"
        ),
    ):
        """Membuat tugas baru untuk proyek tertentu."""
        await self.project_service.get(project_id)

        # handle display order None atau 0
        payload.display_order = await self.task_service.validate_display_order(
            project_id, payload.display_order
        )

        task = await self.task_service.create(
            payload,
            extra_fields={
                "project_id": project_id,
                "parent_id": parent_task_id,
                "created_by": self.user.id,
            },
        )
        return TaskResponse.model_validate(task)

    @r.get("/{project_id}/tasks/{task_id}")
    async def get_detail_task(self, project_id: int, task_id: int):
        """Mendapatkan detail tugas untuk proyek tertentu."""

        await self.project_service.get(project_id)
        task = await self.task_service.get(task_id)
        return TaskResponse.model_validate(task)
