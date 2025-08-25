from __future__ import annotations

from typing import Any, Callable, Optional, Protocol, runtime_checkable

from sqlalchemy import Select, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.project_member_model import ProjectMember
from app.db.models.project_model import Project, StatusProject
from app.db.models.task_assigne_model import TaskAssignee
from app.db.models.task_model import StatusTask, Task
from app.schemas.task import TaskCreate, TaskUpdate


@runtime_checkable
class InterfaceTaskRepository(Protocol):
    """
    Antarmuka (protocol) untuk repositori Task.
    Dirancang untuk memudahkan dependency injection, mocking, dan pengujian.
    Seluruh method bersifat asynchronous.
    """

    async def get(
        self, task_id: int, *, options: list[Any] | None = None
    ) -> Task | None:
        """
        Mengambil satu Task berdasarkan ID.
        - options: daftar SQLAlchemy loader options (mis. selectinload) jika
        diperlukan. Mengembalikan Task atau None jika tidak ditemukan.
        """
        ...

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        custom_query: Callable[[Select], Select] | None = None,
    ) -> list[Task]:
        """
        Mengambil daftar Task yang belum dihapus (soft delete).
        - filters: pasangan kolom->nilai untuk where sederhana (==).
        - order_by: ekspresi order_by SQLAlchemy.
        - custom_query: fungsi untuk memodifikasi Select sebelum dieksekusi.
        """
        ...

    async def create(
        self, payload: TaskCreate, *, extra_fields: dict[str, Any]
    ) -> Task:
        """
        Membuat Task baru dari payload dan field tambahan (mis. project_id,
        display_order). Mengembalikan entitas Task yang sudah dipersist.
        """
        ...

    async def update(self, task: Task, updates: TaskUpdate | dict[str, Any]) -> Task:
        """
        Memperbarui Task berdasarkan data yang diberikan.
        - updates: bisa berupa skema TaskUpdate atau dict field yang ingin
        diperbarui. Mengembalikan Task yang sudah diperbarui.
        """
        ...

    async def soft_delete(self, task: Task) -> None:
        """
        Melakukan soft delete pada Task dengan mengisi kolom deleted_at.
        """
        ...

    async def next_display_order(self, project_id: int) -> int:
        """
        Menghitung nilai display_order berikutnya untuk sebuah proyek.
        Dipakai untuk menjaga urutan tampilan task.
        """
        ...

    async def validate_display_order(
        self, project_id: int, display_order: Optional[int]
    ) -> int:
        """
        Memvalidasi display_order:
        - Jika None/<=0 atau sudah digunakan task lain dalam proyek yang sama,
          akan mengembalikan nilai display_order berikutnya yang valid.
        - Jika valid, mengembalikan nilai yang diberikan.
        """
        ...

    async def assign_user(self, task: Task, user_id: int) -> TaskAssignee:
        """
        Menetapkan user ke sebuah Task (idempotent).
        Jika sudah ter-assign, mengembalikan relasi yang ada.
        """
        ...

    async def get_task_with_assignees(self, task_id: int) -> Task | None:
        """
        Mengambil Task beserta relasi assignees-nya.
        """
        ...

    async def get_project_member_user_ids(self, project_id: int) -> list[int]:
        """
        Mengambil daftar user_id yang menjadi anggota dari sebuah proyek.
        """
        ...

    async def list_subtasks(self, parent_id: int) -> list[Task]:
        """
        Mengambil daftar subtask berdasarkan parent_id.
        """
        ...

    async def detach_all_subtasks_from_section(self, section_task_id: int) -> int:
        """
        Melepas seluruh subtask dari sebuah section (mengosongkan parent_id).
        Mengembalikan jumlah subtask yang terpengaruh.
        """
        ...

    async def cascade_soft_delete_subtasks(self, parent_task_id: int) -> int:
        """
        Melakukan soft delete terhadap seluruh subtask langsung dari sebuah parent
        task. Mengembalikan jumlah subtask yang terpengaruh.
        """
        ...

    async def get_user_task_statistics(self, user_id: int) -> dict:
        """
        Mengembalikan statistik tugas untuk seorang user dalam bentuk dict:
        - total_task
        - task_in_progress
        - task_completed
        - task_cancelled
        Hanya menghitung task dan project yang belum dihapus, serta status
        project/task tertentu.
        """
        ...

    async def unassign_user(self, user_id: int, task_id: int) -> None:
        """
        Menghapus penugasan user dari sebuah task.
        """
        ...


class TaskSQLAlchemyRepository(InterfaceTaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, task_id: int, *, options: list[Any] | None = None
    ) -> Task | None:
        stmt = select(Task).where(Task.id == task_id, Task.deleted_at.is_(None))
        if options:
            stmt = stmt.options(*options)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        custom_query: Callable[[Select], Select] | None = None,
    ) -> list[Task]:
        stmt = select(Task).where(Task.deleted_at.is_(None))
        if filters:
            for k, v in filters.items():
                stmt = stmt.where(getattr(Task, k) == v)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if custom_query is not None:
            stmt = custom_query(stmt)
        res = await self.session.execute(stmt)
        return list(res.scalars())

    async def create(
        self, payload: TaskCreate, *, extra_fields: dict[str, Any]
    ) -> Task:
        data = {**payload.model_dump(), **extra_fields}
        task = Task(**data)
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update(self, task: Task, updates: TaskUpdate | dict[str, Any]) -> Task:
        data = (
            updates.model_dump(exclude_unset=True)  # type: ignore
            if hasattr(updates, "model_dump")
            else dict(updates)
        )
        for k, v in data.items():
            setattr(task, k, v)
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def soft_delete(self, task: Task) -> None:
        task.deleted_at = func.now()
        self.session.add(task)
        await self.session.flush()

    async def next_display_order(self, project_id: int) -> int:
        q = await self.session.execute(
            select(Task)
            .where(Task.project_id == project_id, Task.deleted_at.is_(None))
            .order_by(Task.display_order.desc())
        )
        last = q.scalars().first()
        return 10000 if last is None else (last.display_order + 10000)

    async def validate_display_order(
        self, project_id: int, display_order: Optional[int]
    ) -> int:
        if display_order is None or display_order <= 0:
            return await self.next_display_order(project_id)

        exists_same = await self.session.execute(
            select(Task.id)
            .where(
                Task.project_id == project_id,
                Task.display_order == display_order,
                Task.deleted_at.is_(None),
            )
            .limit(1)
        )
        if exists_same.first():
            return await self.next_display_order(project_id)
        return display_order

    async def assign_user(self, task: Task, user_id: int) -> TaskAssignee:
        res = await self.session.execute(
            select(TaskAssignee)
            .where(TaskAssignee.task_id == task.id, TaskAssignee.user_id == user_id)
            .limit(1)
        )
        ta = res.scalar_one_or_none()
        if ta:
            return ta
        ta = TaskAssignee(task_id=task.id, user_id=user_id)
        self.session.add(ta)
        await self.session.flush()
        await self.session.refresh(ta)
        return ta

    async def get_task_with_assignees(self, task_id: int) -> Task | None:
        return await self.get(task_id, options=[selectinload(Task.assignees)])

    async def get_project_member_user_ids(self, project_id: int) -> list[int]:
        res = await self.session.execute(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_id
            )
        )
        return [row[0] for row in res.all()]

    async def list_subtasks(self, parent_id: int) -> list[Task]:
        res = await self.session.execute(
            select(Task).where(
                Task.parent_id == parent_id, Task.deleted_at.is_(None)
            )
        )
        return list(res.scalars())

    async def detach_all_subtasks_from_section(self, section_task_id: int) -> int:
        subtasks = await self.list_subtasks(section_task_id)
        if not subtasks:
            return 0
        for st in subtasks:
            st.parent_id = None
        self.session.add_all(subtasks)
        await self.session.flush()
        return len(subtasks)

    async def cascade_soft_delete_subtasks(self, parent_task_id: int) -> int:
        subtasks = await self.list_subtasks(parent_task_id)
        for st in subtasks:
            await self.soft_delete(st)
        return len(subtasks)

    async def get_user_task_statistics(self, user_id: int) -> dict:
        stmt = (
            select(
                func.count().label("total_task"),
                func.sum(
                    case((Task.status == StatusTask.IN_PROGRESS, 1), else_=0)
                ).label("task_in_progress"),
                func.sum(
                    case((Task.status == StatusTask.COMPLETED, 1), else_=0)
                ).label("task_completed"),
                func.sum(
                    case((Task.status == StatusTask.CANCELLED, 1), else_=0)
                ).label("task_cancelled"),
            )
            .join(TaskAssignee, TaskAssignee.task_id == Task.id)
            .join(Project, Project.id == Task.project_id)
            .where(
                TaskAssignee.user_id == user_id,
                Task.deleted_at.is_(None),
                Task.status.not_in([StatusTask.PENDING]),
                Project.status.in_([StatusProject.ACTIVE, StatusProject.COMPLETED]),
                Project.deleted_at.is_(None),
            )
        )
        res = await self.session.execute(stmt)
        row = res.first()
        if not row:
            return {
                "total_task": 0,
                "task_in_progress": 0,
                "task_completed": 0,
                "task_cancelled": 0,
            }
        return {
            "total_task": row.total_task or 0,
            "task_in_progress": row.task_in_progress or 0,
            "task_completed": row.task_completed or 0,
            "task_cancelled": row.task_cancelled or 0,
        }

    async def unassign_user(self, user_id: int, task_id: int) -> None:
        stmt = delete(TaskAssignee).where(
            TaskAssignee.user_id == user_id, TaskAssignee.task_id == task_id
        )
        await self.session.execute(stmt)
        await self.session.flush()
