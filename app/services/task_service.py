from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import selectinload

from app.core.domain.events.assignee_task import (
    TaskAssignedAddedEvent,
    TaskAssignedRemovedEvent,
)
from app.core.domain.events.task import (
    SubTasksDetachedFromSectionEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskRenameEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)
from app.core.domain.policies.task import (
    ensure_assignee_is_project_member,
    ensure_only_assignee_can_change_status,
)
from app.db.models.project_member_model import RoleProject
from app.db.models.role_model import Role
from app.db.models.task_model import ResourceType, StatusTask, Task
from app.db.repositories.task_repository import InterfaceTaskRepository
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.milestone import MileStoneCreate
from app.schemas.task import TaskCreate, TaskUpdate
from app.schemas.user import User
from app.utils import exceptions

if TYPE_CHECKING:
    pass


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

    async def get_detail_task(self, *, user: User, task_id: int) -> Task:
        """Mendapatkan detail tugas untuk proyek tertentu.

        Args:
            user (User): Pengguna yang meminta detail tugas.
            task_id (int): ID tugas yang akan diambil detailnya.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
            exceptions.ProjectNotFoundError: Jika proyek tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses.

        Returns:
            Task: Tugas yang diminta.
        """
        task = await self.get(task_id)
        if task is None:
            raise exceptions.TaskNotFoundError

        # pastikan user adalah member project
        project_exists, is_member = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=task.project_id
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_member and user.role != Role.ADMIN:
            raise exceptions.ForbiddenError(
                "hanya anggota proyek yang dapat mengakses sub-tugas"
            )

        return task

    async def list_task(
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

    async def list_subtask(self, *, user: User, task_id: int) -> list[Task]:
        """Mendapatkan daftar sub-tugas untuk tugas tertentu.

        Args:
            task_id (int): ID tugas yang akan diambil sub-tugasnya.

        Returns:
            list[Task]: Daftar sub-tugas yang ditemukan.
        """

        task = await self.get(task_id)
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        project_exists, is_member = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=task.project_id
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_member and user.role != Role.ADMIN:
            raise exceptions.ForbiddenError(
                "hanya anggota proyek yang dapat mengakses sub-tugas"
            )

        return await self.repo.list(
            filters={"parent_id": task.id},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(selectinload(Task.sub_tasks)),
        )

    async def create_task(
        self, *, user: User, parent_id: int, project_id: int, payload: TaskCreate
    ) -> Task:
        """Membuat tugas baru.

        Args:
            payload (TaskCreate): Data untuk tugas baru.
            parent_task_id (int | None): ID tugas induk, jika ada.
            actor (User): Pengguna yang membuat tugas.

        Returns:
            Task: Tugas yang telah dibuat.
        """

        project_exists, is_owner = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=project_id, required_role=RoleProject.OWNER
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_owner and user.role != Role.ADMIN:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat membuat task dalam milestone"
            )

        # Validasi parent: boleh milestone atau task biasa
        parent = await self.uow.task_repo.get(parent_id)
        if (
            not parent
            or parent.project_id != project_id
            or parent.resource_type
            not in (ResourceType.MILESTONE, ResourceType.TASK)
            or getattr(parent, "deleted_at", None)
        ):
            raise exceptions.TaskNotFoundError("Milestone tidak ditemukan")

        # Jika parent adalah task biasa, pastikan ia terhubung ke milestone
        if parent.resource_type == ResourceType.TASK:
            milestone = await self.uow.task_repo.get_ancestor_milestone(parent.id)
            if not milestone:
                # Ubah ke BadRequestError jika punya
                raise exceptions.TaskNotFoundError(
                    "Parent belum terhubung ke milestone"
                )

        payload.display_order = await self.repo.validate_display_order(
            project_id=project_id, display_order=payload.display_order
        )

        task = await self.uow.task_repo.create(
            payload=payload,
            extra_fields={
                "project_id": project_id,
                "created_by": user.id,
                "parent_id": parent_id,
                "resource_type": ResourceType.TASK,
            },
        )

        self.uow.add_event(
            TaskCreatedEvent(
                performed_by=task.id,
                project_id=task.project_id,
                task_id=task.id,
                created_by=user.id,
                item_type=task.resource_type,
                task_name=task.name,
            )
        )
        return task

    async def update_task(
        self, user_id: int, task_id: int, payload: TaskUpdate
    ) -> Task:
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
            TaskUpdatedEvent(
                performed_by=updated.id,
                project_id=updated.project_id,
                task_id=task.id,
                updated_by=user_id,
            )
        )

        if payload.name and payload.name != task.name:
            self.uow.add_event(
                TaskRenameEvent(
                    performed_by=updated.id,
                    project_id=updated.project_id,
                    task_id=task.id,
                    updated_by=user_id,
                    before=task.name,
                    after=payload.name,
                )
            )

        if payload.status and payload.status != task.status:
            self.uow.add_event(
                TaskStatusChangedEvent(
                    performed_by=user_id,
                    task_id=updated.id,
                    project_id=updated.project_id,
                    old_status=task.status or "",
                    new_status=payload.status,
                )
            )

        return updated

    async def delete_task(self, user_id: int, task_id: int) -> None:
        """Menghapus tugas berdasarkan ID.

        Args:
            task_id (int): ID tugas yang akan dihapus.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
        """
        task = await self.repo.get(task_id, options=[selectinload(Task.sub_tasks)])
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        if task.resource_type == ResourceType.MILESTONE:
            detached = await self.repo.detach_all_subtasks_from_section(task.id)
            self.uow.add_event(
                SubTasksDetachedFromSectionEvent(
                    user_id=user_id,
                    section_task_id=task.id,
                    project_id=task.project_id,
                    detached_count=detached,
                )
            )
        else:
            await self.repo.cascade_soft_delete_subtasks(task.id)

        await self.repo.soft_delete(task)
        self.uow.add_event(
            TaskDeletedEvent(
                performed_by=task.id,
                project_id=task.project_id,
                task_name=task.name,
                deleted_by=user_id,
            )
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

        old = getattr(task.status, "name", str(task.status))
        updated = await self.repo.update(task, {"status": new_status})
        self.uow.add_event(
            TaskStatusChangedEvent(
                performed_by=actor_user_id,
                task_id=task.id,
                project_id=task.project_id,
                old_status=old,
                new_status=getattr(new_status, "name", str(new_status)),
            )
        )
        return updated

    async def assign_user(self, actor_id, task_id: int, *, user: User) -> None:
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

        await self.repo.assign_user(task, user.id)
        self.uow.add_event(
            TaskAssignedAddedEvent(
                task_id=task.id,
                performed_by=task.id,
                project_id=task.project_id,
                user_id=actor_id,
                assignee_id=user.id,
                assignee_name=user.name,
            )
        )

    async def unassign_user(self, actor_id: int, user: User, task: Task) -> None:
        """Menghapus penugasan pengguna dari tugas tertentu.

        Args:
            actor_id (int): ID pengguna yang mencoba menghapus penugasan.
            user (User): Pengguna yang akan dihapus penugasannya.
            task (Task): Tugas yang akan dihapus penugasannya.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
            exceptions.UserNotInProjectError: Jika pengguna tidak terdaftar di
                proyek.
        """

        member_ids = await self.repo.get_project_member_user_ids(task.project_id)
        ensure_assignee_is_project_member(
            project_member_user_ids=member_ids, target_user_id=user.id
        )

        await self.repo.unassign_user(user.id, task.id)

        self.uow.add_event(
            TaskAssignedRemovedEvent(
                task_id=task.id,
                performed_by=task.id,
                project_id=task.project_id,
                user_id=actor_id,
                assignee_id=user.id,
                assignee_name=user.name,
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

    async def create_milestone(
        self, *, user: User, project_id: int, payload: MileStoneCreate
    ) -> Task:
        """Membuat Milestone baru

        Args:
            user (User): Pengguna yang membuat milestone.
            project_id (int): ID proyek tempat milestone dibuat.
            payload (MileStoneCreate): Data untuk milestone baru.
        """

        project_exists, is_owner = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=project_id, required_role=RoleProject.OWNER
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat membuat milestone"
            )

        milestone = await self.uow.task_repo.create(
            payload=TaskCreate(
                name=payload.name,
                status=payload.status,
                display_order=payload.display_order,
            ),
            extra_fields={
                "project_id": project_id,
                "created_by": user.id,
                "resource_type": ResourceType.MILESTONE,
            },
        )

        # TODO : Tambah event milestone created

        return milestone

    async def list_milestone_with_task(
        self, *, project_id: int, user: User
    ) -> list[Task]:
        project_exists, is_member = await self.uow.project_repo.get_membership_flags(
            user_id=user.id, project_id=project_id
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if user.role != Role.ADMIN and not is_member:
            raise exceptions.ForbiddenError(
                "Hanya anggota proyek yang dapat melihat milestone"
            )

        return await self.uow.task_repo.list(
            filters={"project_id": project_id, "parent_id": None},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(
                selectinload(Task.sub_tasks, recursion_depth=1)
            ),
        )
