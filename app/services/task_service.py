from typing import Any

from sqlalchemy.orm import selectinload

from app.core.domain.events.task import (
    SubTasksDetachedFromSectionEvent,
    TaskAssignedEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)
from app.core.domain.policies.task import (
    ensure_assignee_is_project_member,
    ensure_only_assignee_can_change_status,
)
from app.db.models.task_model import ResourceType, StatusTask, Task
from app.db.repositories.task_repository import InterfaceTaskRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import User
from app.utils import exceptions


class TaskService:
    def __init__(self, uow: UnitOfWork, repo: InterfaceTaskRepository) -> None:
        self.uow = uow
        self.repo = repo

    async def get(
        self, task_id: int, *, options: list[Any] | None = None
    ) -> Task | None:
        """Mendapatkan tugas berdasarkan ID.

        Args:
            task_id (int): ID tugas yang akan diambil.
            options (list[Any] | None, optional): Opsi tambahan untuk kueri.
                Defaults to None.

        Returns:
            Task | None: Tugas yang diminta, atau None jika tidak ditemukan.
        """
        return await self.repo.get(task_id, options=options)

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        custom_query=None,
    ) -> list[Task]:
        """Mendapatkan daftar tugas.

        Args:
            filters (dict[str, Any] | None, optional): Filter untuk daftar tugas.
                Defaults to None.
            order_by (Any | None, optional): Urutan hasil. Defaults to None.
            custom_query (_type_, optional): Kuery kustom untuk daftar tugas.
                Defaults to None.

        Returns:
            list[Task]: Daftar tugas yang ditemukan.
        """
        return await self.repo.list(
            filters=filters, order_by=order_by, custom_query=custom_query
        )

    async def create_task(
        self, payload: TaskCreate, *, parent_task_id: int | None, actor: User
    ) -> Task:
        """Membuat tugas baru.

        Args:
            payload (TaskCreate): Data untuk tugas baru.
            parent_task_id (int | None): ID tugas induk, jika ada.
            actor (User): Pengguna yang membuat tugas.

        Returns:
            Task: Tugas yang telah dibuat.
        """
        payload.display_order = await self.repo.validate_display_order(
            payload.project_id, payload.display_order
        )
        task = await self.repo.create(
            payload,
            extra_fields={"parent_id": parent_task_id, "created_by": actor.id},
        )
        self.uow.add_event(
            TaskCreatedEvent(
                task_id=task.id, project_id=task.project_id, created_by=actor.id
            )
        )
        return task

    async def update_task(self, task_id: int, payload: TaskUpdate) -> Task:
        """Memperbarui tugas yang ada.

        Args:
            task_id (int): ID tugas yang akan diperbarui.
            payload (TaskUpdate): Data pembaruan untuk tugas.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.

        Returns:
            Task: Tugas yang telah diperbarui.
        """
        task = await self.repo.get(task_id)
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")
        updated = await self.repo.update(task, payload)
        self.uow.add_event(
            TaskUpdatedEvent(task_id=updated.id, project_id=updated.project_id)
        )
        return updated

    async def delete_task(self, task_id: int) -> None:
        """Menghapus tugas berdasarkan ID.

        Args:
            task_id (int): ID tugas yang akan dihapus.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
        """
        task = await self.repo.get(task_id, options=[selectinload(Task.sub_tasks)])
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        if task.resource_type == ResourceType.SECTION:
            detached = await self.repo.detach_all_subtasks_from_section(task.id)
            self.uow.add_event(
                SubTasksDetachedFromSectionEvent(
                    section_task_id=task.id,
                    project_id=task.project_id,
                    detached_count=detached,
                )
            )
        else:
            await self.repo.cascade_soft_delete_subtasks(task.id)

        await self.repo.soft_delete(task)
        self.uow.add_event(
            TaskDeletedEvent(task_id=task.id, project_id=task.project_id)
        )

    # Status change
    async def change_status(
        self, task_id: int, *, new_status: StatusTask, actor_user_id: int
    ) -> Task:
        """Mengubah status tugas.

        Args:
            task_id (int): ID tugas yang akan diubah statusnya.
            new_status (StatusTask): Status baru yang akan diterapkan.
            actor_user_id (int): ID pengguna yang mencoba mengubah status tugas.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki izin untuk
                mengubah status tugas.

        Returns:
            Task: Tugas yang telah diperbarui.
        """
        task = await self.repo.get_task_with_assignees(task_id)
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        ensure_only_assignee_can_change_status(
            task_assignee_user_ids=[a.user_id for a in task.assignees],
            actor_user_id=actor_user_id,
        )

        # ensure_task_status_transition(task.status, new_status)

        old = getattr(task.status, "name", str(task.status))
        updated = await self.repo.update(task, {"status": new_status})
        self.uow.add_event(
            TaskStatusChangedEvent(
                task_id=task.id,
                project_id=task.project_id,
                old_status=old,
                new_status=getattr(new_status, "name", str(new_status)),
            )
        )
        return updated

    async def assign_user(self, task_id: int, *, user: User) -> None:
        """Menugaskan pengguna ke tugas tertentu.

        Args:
            task_id (int): ID tugas yang akan ditugaskan.
            user_info (User): Informasi pengguna yang akan ditugaskan.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
            exceptions.UserNotInProjectError: Jika pengguna tidak terdaftar di
                proyek.

        Returns:
            TaskAssignee: Objek penugasan tugas yang berhasil dibuat.
        """
        task = await self.repo.get(task_id)
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        member_ids = await self.repo.get_project_member_user_ids(task.project_id)
        ensure_assignee_is_project_member(
            project_member_user_ids=member_ids, target_user_id=user.id
        )

        ta = await self.repo.assign_user(task, user.id)
        self.uow.add_event(
            TaskAssignedEvent(
                task_id=task.id, project_id=task.project_id, user_id=ta.user_id
            )
        )

    async def validate_display_order(
        self, project_id: int, display_order: int | None
    ) -> int:
        """Validasi urutan tampilan tugas.

        Args:
            project_id (int): ID proyek yang terkait dengan tugas.
            display_order (int): Urutan tampilan yang akan divalidasi.

        Raises:
            ValueError: Jika urutan tampilan tidak valid.
        """
        return await self.repo.validate_display_order(project_id, display_order)

    async def get_user_task_statistics(self, user_id: int) -> dict:
        """Mengambil statistik tugas untuk pengguna tertentu.

        Args:
            user_id (int): ID pengguna yang akan diambil statistik tugasnya.

        Returns:
            dict: Statistik tugas untuk pengguna tertentu.
        """
        return await self.repo.get_user_task_statistics(user_id)
        return await self.repo.get_user_task_statistics(user_id)
