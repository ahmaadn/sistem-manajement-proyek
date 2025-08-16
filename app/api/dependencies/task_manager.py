from fastapi import Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.models.task_model import Task
from app.schemas.task import TaskCreate
from app.utils.common import ErrorCode


class TaskManager:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(
        self,
        task_id: int,
        *,
        allow_deleted: bool = False,
        return_none_if_not_found: bool = False,
    ) -> Task | None:
        task_item = await self.session.get(Task, task_id)

        if task_item is None:
            if return_none_if_not_found:
                return None
            self._log_not_found(task_id)
            raise self._exception_item_not_found()

        if task_item.is_deleted and not allow_deleted:
            if return_none_if_not_found:
                return None
            self._log_deleted(task_id)
            raise self._exception_item_not_found()

        return task_item

    async def create(self, project_id: int, task_data: TaskCreate) -> Task:
        """membuat tugas baru untuk proyek tertentu.

        Args:
            project_id (int): ID proyek tempat tugas akan dibuat.
            task_data (TaskCreate): Data tugas yang akan dibuat.
        """

        # TODO: Handle display order

        # Cast ke dalam model
        task_item = Task(
            name=task_data.name,
            description=task_data.description,
            resource_type=task_data.resource_type,
            status=task_data.status,
            priority=task_data.priority,
            display_order=1000,
            due_date=task_data.due_date,
            start_date=task_data.start_date,
            estimated_duration=task_data.estimated_duration,
            project_id=project_id,
            created_by=1,
        )

        return await self._asave(task_item)

    async def _asave(self, data: Task):
        self.session.add(data)
        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            raise
        await self.session.refresh(data)
        return data

    @staticmethod
    def _log_not_found(project_id: int) -> None:
        print(f"[ProjectManager] Project id={project_id} tidak ditemukan.")

    @staticmethod
    def _log_deleted(project_id: int) -> None:
        print(
            f"[ProjectManager] Project id={project_id} sudah dihapus (soft delete)."
        )

    @staticmethod
    def _exception_item_not_found(**extra) -> HTTPException:
        """
        Membuat exception jika item tidak ditemukan.
        """
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error_code": ErrorCode.PROJECT_NOT_FOUND,
                "message": "Item tidak ditemukan.",
                **extra,
            },
        )


def get_task_manager(
    session: AsyncSession = Depends(get_async_session),
) -> TaskManager:
    return TaskManager(session=session)
