from fastapi import APIRouter, Depends, Path, Query
from fastapi_utils.cbv import cbv

from app.api.dependencies.project_manager import ProjectManager, get_project_manager
from app.api.dependencies.task_manager import TaskManager, get_task_manager
from app.api.dependencies.user import get_current_user
from app.schemas.task import TaskCreate
from app.schemas.user import UserProfile

r = router = APIRouter(prefix="/project", tags=["Task", "Project"])


@cbv(r)
class _Task:
    user: UserProfile = Depends(get_current_user)
    task_manager: TaskManager = Depends(get_task_manager)
    project_manager: ProjectManager = Depends(get_project_manager)

    @r.get("/{project_id}/tasks")
    async def get_tasks(self, project_id: str):
        """Mendapatkan daftar tugas untuk proyek tertentu."""

    @r.post("/{project_id}/tasks")
    async def create_task(
        self,
        data_task: TaskCreate,
        project_id: int = Path(default=..., description="ID proyek"),
        parent_task_id: int | None = Query(
            default=None, description="ID tugas induk jika ada"
        ),
    ):
        """Membuat tugas baru untuk proyek tertentu."""
        await self.project_manager.get(project_id)

        task = await self.task_manager.create(
            project_id=project_id, task_data=data_task
        )

    @r.get("/{project_id}/tasks/{task_id}")
    async def get_detail_task(self, project_id: str, task_id: str):
        """Mendapatkan detail tugas untuk proyek tertentu."""
