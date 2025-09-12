from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy.orm import selectinload

from app.core.domain.events.assignee_task import (
    TaskAssignedAddedEvent,
    TaskAssignedRemovedEvent,
)
from app.core.domain.events.task import (
    TaskRenameEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)
from app.core.policies.task import (
    ensure_assignee_is_project_member,
    ensure_only_assignee_can_change_status,
)
from app.db.models.project_member_model import RoleProject
from app.db.models.role_model import Role
from app.db.models.task_assigne_model import TaskAssignee
from app.db.models.task_model import StatusTask, Task
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.task import (
    TaskAssigneeRead,
    TaskAttachmentRead,
    TaskCreate,
    TaskDetail,
    TaskUpdate,
)
from app.schemas.user import User
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions

if TYPE_CHECKING:
    pass


class TaskService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.repo = uow.task_repo

        self.pegawai_service = PegawaiService()

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
        return await self.repo.get_by_id(task_id, options=options)

    async def get_detail_task(self, *, user: User, task_id: int) -> TaskDetail:
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
        task = await self.repo.get_by_id(
            task_id,
            options=[
                selectinload(Task.assignees),
                selectinload(Task.sub_tasks),
                selectinload(Task.attachments),
            ],
        )
        if task is None:
            raise exceptions.TaskNotFoundError

        # pastikan user adalah member proyek
        is_member = await self.uow.project_repo.ensure_member_in_project(
            user_id=user.id, project_id=task.project_id
        )
        if not is_member and user.role != Role.ADMIN:
            raise exceptions.ForbiddenError(
                "hanya anggota proyek yang dapat mengakses sub-tugas"
            )

        # get user
        assigns_user_ids = [assignee.user_id for assignee in task.assignees]
        assigns_users = await self.pegawai_service.list_user_by_ids(
            data=assigns_user_ids
        )
        users = [
            TaskAssigneeRead(
                user_id=user.id,
                name=user.name,
                email=user.email,
                profile_url=user.profile_url,
            )
            for user in assigns_users
            if user
        ]

        # attachments
        attachments = [
            TaskAttachmentRead(
                id=attachment.id,
                file_name=attachment.file_name,
                file_path=attachment.file_path,
                file_size=attachment.file_size,
                created_at=attachment.created_at,
                mime_type=attachment.mime_type,
            )
            for attachment in await self.uow.attachment_repo.list_by_task_without_comment(
                task_id=task.id
            )
        ]

        return TaskDetail(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status,
            priority=task.priority,
            display_order=task.display_order,
            due_date=task.due_date,
            start_date=task.start_date,
            estimated_duration=task.estimated_duration,
            assignees=users,
            sub_tasks=task.sub_tasks,  # type: ignore # auto cast ke type list[SubSubTaskResponse]
            attachments=attachments,
        )

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
        return await self.repo.list_by_filters(
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

        (
            project_exists,
            is_member,
        ) = await self.uow.project_repo.get_project_membership_flags(
            user_id=user.id, project_id=task.project_id
        )

        if not project_exists:
            raise exceptions.ProjectNotFoundError("Project tidak ditemukan")

        if not is_member and user.role != Role.ADMIN:
            raise exceptions.ForbiddenError(
                "hanya anggota proyek yang dapat mengakses sub-tugas"
            )

        return await self.repo.list_by_filters(
            filters={"parent_id": task.id},
            order_by=Task.display_order,
            custom_query=lambda s: s.options(selectinload(Task.sub_tasks)),
        )

    async def create_task(
        self, *, user: User, milestone_id: int, payload: TaskCreate
    ) -> Task:
        """Membuat tugas baru.

        Args:
            user (User): Pengguna yang membuat tugas.
            payload (TaskCreate): Data untuk tugas baru.
            milestone_id (int | None): ID milestone

        Returns:
            Task: Tugas yang telah dibuat.
        """
        # get milestone
        milestone = await self.uow.milestone_repo.get_by_id(
            milestone_id=milestone_id
        )
        if not milestone:
            raise exceptions.MilestoneNotFoundError("Milestone tidak ditemukan")

        # Cek status member
        is_owner = await self.uow.project_repo.is_user_owner_of_project(
            user_id=user.id, project_id=milestone.project_id
        )

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat membuat task dalam milestone"
            )

        # buat task
        data = payload.model_dump(exclude_unset=True)
        estimated_duration = 0

        data.update(
            {
                "created_by": user.id,
                "milestone_id": milestone.id,
                "project_id": milestone.project_id,
                "display_order": await self.repo.ensure_valid_display_order(
                    project_id=milestone.project_id,
                    display_order=payload.display_order,
                ),
                "estimated_duration": estimated_duration,  # Set 0 untuk sementara
            }
        )

        task = await self.uow.task_repo.create_task(payload=data)

        # Jika start_date tidak diisi, set ke created_at
        start_date = task.created_at if task.start_date is None else task.start_date

        # Hitung estimasi durasi dalam menit dari due_date - start_date.
        # Jika salah satu bernilai None, jangan dihitung.
        if (
            task.estimated_duration is None or task.estimated_duration == 0
        ) and task.due_date:
            delta_minutes = int((task.due_date - start_date).total_seconds() // 60)
            estimated_duration = max(0, delta_minutes)

        return await self.uow.task_repo.update_task(
            task,
            {"estimated_duration": estimated_duration, "start_date": start_date},
        )

    async def create_subtask(
        self, *, user: User, task_id: int, payload: TaskCreate
    ) -> Task:
        """Membuat tugas baru.

        Args:
            user (User): Pengguna yang membuat tugas.
            payload (TaskCreate): Data untuk tugas baru.
            milestone_id (int | None): ID milestone

        Returns:
            Task: Tugas yang telah dibuat.
        """
        # get milestone
        parent_task = await self.repo.get_by_id(task_id)
        if not parent_task:
            raise exceptions.TaskNotFoundError("Task tidak ditemukan")

        # Cek status member
        is_owner = await self.uow.project_repo.is_user_owner_of_project(
            user_id=user.id, project_id=parent_task.project_id
        )

        if not is_owner:
            raise exceptions.ForbiddenError(
                "Hanya owner proyek yang dapat membuat task dalam milestone"
            )

        # buat task
        data = payload.model_dump(exclude_unset=True)
        data.update(
            {
                "created_by": user.id,
                "milestone_id": parent_task.milestone_id,
                "project_id": parent_task.project_id,
                "parent_id": parent_task.id,
                "display_order": await self.repo.ensure_valid_display_order(
                    project_id=parent_task.project_id,
                    display_order=payload.display_order,
                ),
            }
        )
        return await self.uow.task_repo.create_task(payload=data)

    async def update_task(
        self, *, user: User, task_id: int, payload: TaskUpdate
    ) -> Task:
        """Memperbarui tugas yang ada.

        Args:
            task_id (int): ID tugas yang akan diperbarui.
            payload (TaskUpdate): Data pembaruan untuk tugas.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
            exceptions.ForbiddenError: Jika pengguna tidak memiliki akses.

        Returns:
            Task: Tugas yang telah diperbarui.
        """
        task = await self.repo.get_by_id(task_id)

        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        # cek status member (Owner)
        is_owner = await self.uow.project_repo.ensure_member_in_project(
            user_id=user.id,
            project_id=task.project_id,
            required_role=RoleProject.OWNER,
        )

        # hanya owner project dan admin yang bisa update task
        if not is_owner and user.role != Role.ADMIN:
            raise exceptions.ForbiddenError(
                "Tidak punya akses untuk mengupdate task"
            )

        task_update_data: dict[str, Any] = payload.model_dump(exclude_unset=True)

        # handle jika status berubah ke COMPLETED atau dari COMPLETED ke status lain
        if payload.status:
            task_update_data.update(
                **self.handle_completed_status(payload.status, task, task.status)
            )

        updated = await self.repo.update_task(task, task_update_data)

        self.uow.add_event(
            TaskUpdatedEvent(
                performed_by=updated.id,
                project_id=updated.project_id,
                task_id=task.id,
                updated_by=user.id,
            )
        )

        if payload.name and payload.name != task.name:
            self.uow.add_event(
                TaskRenameEvent(
                    performed_by=updated.id,
                    project_id=updated.project_id,
                    task_id=task.id,
                    updated_by=user.id,
                    before=task.name,
                    after=payload.name,
                )
            )

        if payload.status and payload.status != task.status:
            self.uow.add_event(
                TaskStatusChangedEvent(
                    performed_by=user.id,
                    task_id=updated.id,
                    project_id=updated.project_id,
                    old_status=task.status or "",
                    new_status=payload.status,
                )
            )

        return updated

    async def delete_task(self, *, user: User, task_id: int) -> None:
        """Menghapus tugas berdasarkan ID.

        Args:
            task_id (int): ID tugas yang akan dihapus.

        Raises:
            exceptions.TaskNotFoundError: Jika tugas tidak ditemukan.
        """
        task = await self.repo.get_by_id(
            task_id, options=[selectinload(Task.sub_tasks)]
        )
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        is_owner = await self.uow.project_repo.ensure_member_in_project(
            user_id=user.id,
            project_id=task.project_id,
            required_role=RoleProject.OWNER,
        )

        if not is_owner:
            raise exceptions.ForbiddenError("Tidak punya akses untuk menghapus task")

        # delete subtask
        await self.repo.cascade_hard_delete_subtasks(task.id)
        # kemudian delete task
        await self.repo.hard_delete_task(task)

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

        # Mendapatkan task beserta assignees-nya
        task = await self.repo.get_by_id_with_assignees(task_id)
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        # pastikan hanya assignee (user yang ditugaskan) yang bisa mengubah status
        ensure_only_assignee_can_change_status(
            task_assignee_user_ids=[a.user_id for a in task.assignees],
            actor_user_id=actor_user_id,
        )

        prev_status = task.status
        payload_update: dict[str, Any] = {"status": new_status}

        # handle jika status berubah ke COMPLETED atau dari COMPLETED ke status lain
        payload_update.update(
            **self.handle_completed_status(new_status, task, prev_status)
        )

        task = await self.repo.update_task(task, payload_update)

        # catat event
        self.uow.add_event(
            TaskStatusChangedEvent(
                performed_by=actor_user_id,
                task_id=task.id,
                project_id=task.project_id,
                old_status=prev_status,
                new_status=getattr(new_status, "name", str(new_status)),
            )
        )
        return task

    def handle_completed_status(
        self,
        new_status: StatusTask,
        task: Task,
        prev_status: StatusTask,
    ) -> dict[str, Any]:
        """Mengelola status tugas yang telah selesai.

        Args:
            new_status (StatusTask): Status baru yang akan diterapkan.
            task (Task): Tugas yang akan diperbarui.
            prev_status (StatusTask): Status sebelumnya dari tugas.

        Returns:
            dict[str, Any]: Payload yang berisi pembaruan untuk tugas.
        """
        payload_update = {}
        if new_status == StatusTask.COMPLETED:
            # Jika status diubah ke COMPLETED, set tanggal selesai (completed_at)
            completed_at = datetime.now(timezone.utc)

            # Hitung durasi penyelesaian tugas dalam menit,
            # yaitu selisih antara start_date dan completed_at dan
            # dibatasi minimal 0 menit
            finish_duration = max(
                (
                    (completed_at - task.start_date).total_seconds() // 60
                    if task.start_date
                    else 0
                ),
                0,
            )

            payload_update.update(
                completed_at=completed_at, finish_duration=finish_duration
            )
        elif (
            new_status
            in {StatusTask.CANCELLED, StatusTask.PENDING, StatusTask.IN_PROGRESS}
            and prev_status == StatusTask.COMPLETED
        ):
            # Jika status diubah dari COMPLETED ke status lain, reset completed_at
            # dan finish_duration
            payload_update.update(completed_at=None, finish_duration=0)
        elif task.completed_at is not None:
            payload_update.update(completed_at=None, finish_duration=0)
        return payload_update

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
        task = await self.repo.get_by_id(task_id)
        if not task:
            raise exceptions.TaskNotFoundError("Task not found")

        member_ids = await self.repo.get_project_member_user_ids(task.project_id)
        ensure_assignee_is_project_member(
            project_member_user_ids=member_ids, target_user_id=user.id
        )

        await self.repo.assign_user_to_task(task, user.id)
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

        await self.repo.unassign_user_from_task(user.id, task.id)

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
        return await self.repo.ensure_valid_display_order(project_id, display_order)

    async def get_user_task_statistics(self, user_id: int) -> dict:
        """Mengambil statistik tugas untuk pengguna tertentu.

        Args:
            user_id (int): ID pengguna yang akan diambil statistik tugasnya.

        Returns:
            dict: Statistik tugas untuk pengguna tertentu.
        """
        return await self.repo.get_user_task_statistics(user_id)

    async def list_user_tasks(self, *, user: User):
        return await self.repo.list_by_filters(
            order_by=Task.display_order,
            custom_query=lambda s: s.join(
                TaskAssignee, TaskAssignee.task_id == Task.id
            )
            .where(TaskAssignee.user_id == user.id)
            .distinct()
            .options(selectinload(Task.sub_tasks)),
        )
