from __future__ import annotations

from datetime import date
from typing import Any, Callable, Optional, Protocol, Sequence, runtime_checkable

from sqlalchemy import Select, case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.models.task_assigne_model import TaskAssignee
from app.db.models.task_model import PriorityLevel, StatusTask, Task
from app.schemas.task import TaskUpdate


@runtime_checkable
class InterfaceTaskRepository(Protocol):
    """
    Antarmuka (protocol) untuk repositori Task.
    Dirancang untuk memudahkan dependency injection, mocking, dan pengujian.
    Seluruh method bersifat asynchronous.
    """

    async def get_by_id(
        self, task_id: int, *, options: list[Any] | None = None
    ) -> Task | None:
        """
        Mengambil satu Task berdasarkan ID.
        - options: daftar SQLAlchemy loader options (mis. selectinload) jika
        diperlukan. Mengembalikan Task atau None jika tidak ditemukan.
        """
        ...

    async def list_by_filters(
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

    async def create_task(self, *, payload: dict[str, Any]) -> Task:
        """
        Membuat Task baru dari payload dan field tambahan (mis. project_id,
        display_order). Mengembalikan entitas Task yang sudah dipersist.
        """
        ...

    async def update_task(
        self, task: Task, updates: TaskUpdate | dict[str, Any]
    ) -> Task:
        """
        Memperbarui Task berdasarkan data yang diberikan.
        - updates: bisa berupa skema TaskUpdate atau dict field yang ingin
        diperbarui. Mengembalikan Task yang sudah diperbarui.
        """
        ...

    async def hard_delete_task(self, task: Task) -> None:
        """
        Melakukan soft delete pada Task dengan mengisi kolom deleted_at.
        """
        ...

    async def get_next_display_order(self, project_id: int) -> int:
        """
        Menghitung nilai display_order berikutnya untuk sebuah proyek.
        Dipakai untuk menjaga urutan tampilan task.
        """
        ...

    async def ensure_valid_display_order(
        self, project_id: int, display_order: Optional[int]
    ) -> int:
        """
        Memvalidasi display_order:
        - Jika None/<=0 atau sudah digunakan task lain dalam proyek yang sama,
          akan mengembalikan nilai display_order berikutnya yang valid.
        - Jika valid, mengembalikan nilai yang diberikan.
        """
        ...

    async def assign_user_to_task(
        self, *, task: Task, target_user_id: int
    ) -> TaskAssignee:
        """
        Menetapkan user ke sebuah Task (idempotent).
        Jika sudah ter-assign, mengembalikan relasi yang ada.
        """
        ...

    async def get_by_id_with_assignees(self, task_id: int) -> Task | None:
        """
        Mengambil Task beserta relasi assignees-nya.
        """
        ...

    async def get_project_member_user_ids(self, project_id: int) -> list[int]:
        """
        Mengambil daftar user_id yang menjadi anggota dari sebuah proyek.
        """
        ...

    async def list_subtasks_by_parent(self, parent_id: int) -> list[Task]:
        """
        Mengambil daftar subtask berdasarkan parent_id.
        """
        ...

    async def detach_all_subtasks_from_section_parent(
        self, section_task_id: int
    ) -> int:
        """
        Melepas seluruh subtask dari sebuah section (mengosongkan parent_id).
        Mengembalikan jumlah subtask yang terpengaruh.
        """
        ...

    async def cascade_hard_delete_subtasks(self, parent_task_id: int) -> int:
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

    async def get_overall_task_statistics(self) -> dict:
        """
        Mengembalikan statistik semua tugas:
        - total_task
        - task_in_progress
        - task_completed
        - task_cancelled
        Hanya menghitung task dan project yang belum dihapus, serta status
        project/task tertentu.
        """
        ...

    async def unassign_user_from_task(
        self, *, target_user_id: int, task_id: int
    ) -> None:
        """
        Menghapus penugasan user dari sebuah task.
        """
        ...

    async def is_user_member_of_task_project(
        self, task_id: int, user_id: int
    ) -> bool:
        """
        Mengecek apakah user adalah member dari project tempat task tersebut berada.
        """
        ...

    async def is_task_in_active_project(self, task_id: int) -> bool:
        """
        Mengecek apakah task berada pada project yang masih aktif dan tidak dihapus.

        Args:
            task_id: ID task yang akan dicek.

        Returns:
            bool: True jika project aktif, False jika tidak.
        """
        ...

    async def is_user_owner_of_tasks_project(
        self, user_id: int, task_id: int
    ) -> bool:
        """Mengecek apakah user adalah pemilik proyek dari task yang diberikan.

        Args:
            user_id (int): ID user yang akan dicek.
            task_id (int): ID task yang akan dicek.

        Returns:
            bool: True jika user adalah pemilik proyek, False jika tidak.
        """
        ...

    async def get_project_member_user_ids_by_task(
        self, task_id: int
    ) -> Sequence[int]:
        """
        Mengambil daftar user_id yang menjadi anggota dari sebuah proyek.
        """
        ...

    async def get_report_summary_priority(self, project_id: int) -> dict[str, int]:
        """Mengambil ringkasan laporan berdasarkan prioritas.

        Args:
            project_id (int): ID proyek yang akan diambil laporannya.

        Returns:
            dict[str, int]: Ringkasan laporan berdasarkan prioritas.
        """
        ...

    async def get_report_assignee_stats(self, project_id: int) -> list[dict]:
        """
        Kembalikan statistik penugasan untuk proyek tertentu.

        Args:
            project_id (int): ID proyek yang akan diambil statistiknya.

        Returns:
            list[dict]: Daftar statistik penugasan untuk proyek.
        """
        ...

    async def get_report_weekly_stats(
        self, project_id: int, start_day: date, end_day: date
    ) -> dict[date, tuple[int, int]]:
        """
        Weekly (7 hari) agregasi berdasarkan (updated_at || created_at)
        Return dict[date] = (task_complete, task_not_complete)
        """
        ...


class TaskSQLAlchemyRepository(InterfaceTaskRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self, task_id: int, *, options: list[Any] | None = None
    ) -> Task | None:
        stmt = select(Task).where(Task.id == task_id)
        if options:
            stmt = stmt.options(*options)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_filters(
        self,
        *,
        filters: dict[str, Any] | None = None,
        order_by: Any | None = None,
        custom_query: Callable[[Select], Select] | None = None,
    ) -> list[Task]:
        stmt = select(Task)
        if filters:
            for k, v in filters.items():
                stmt = stmt.where(getattr(Task, k) == v)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if custom_query is not None:
            stmt = custom_query(stmt)
        res = await self.session.execute(stmt)
        return list(res.scalars())

    async def create_task(self, *, payload: dict[str, Any]) -> Task:
        task = Task(**payload)
        self.session.add(task)
        await self.session.flush()
        await self.session.refresh(task)
        return task

    async def update_task(
        self, task: Task, updates: TaskUpdate | dict[str, Any]
    ) -> Task:
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

    async def hard_delete_task(self, task: Task) -> None:
        await self.session.delete(task)
        await self.session.flush()

    async def get_next_display_order(self, project_id: int) -> int:
        q = await self.session.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.display_order.desc())
        )
        last = q.scalars().first()
        return 1000 if last is None else (last.display_order + 1000)

    async def ensure_valid_display_order(
        self, project_id: int, display_order: Optional[int]
    ) -> int:
        if display_order is None or display_order <= 0:
            return await self.get_next_display_order(project_id)

        exists_same = await self.session.execute(
            select(Task.id)
            .where(
                Task.project_id == project_id,
                Task.display_order == display_order,
            )
            .limit(1)
        )
        if exists_same.first():
            return await self.get_next_display_order(project_id)
        return display_order

    async def assign_user_to_task(
        self, *, task: Task, target_user_id: int
    ) -> TaskAssignee:
        res = await self.session.execute(
            select(TaskAssignee)
            .where(
                TaskAssignee.task_id == task.id,
                TaskAssignee.user_id == target_user_id,
            )
            .limit(1)
        )
        ta = res.scalar_one_or_none()
        if ta:
            return ta
        ta = TaskAssignee(task_id=task.id, user_id=target_user_id)
        self.session.add(ta)
        await self.session.flush()
        await self.session.refresh(ta)
        return ta

    async def get_by_id_with_assignees(self, task_id: int) -> Task | None:
        return await self.get_by_id(task_id, options=[selectinload(Task.assignees)])

    async def get_project_member_user_ids(self, project_id: int) -> list[int]:
        res = await self.session.execute(
            select(ProjectMember.user_id).where(
                ProjectMember.project_id == project_id
            )
        )
        return [row[0] for row in res.all()]

    async def list_subtasks_by_parent(self, parent_id: int) -> list[Task]:
        res = await self.session.execute(
            select(Task).where(
                Task.parent_id == parent_id,
            )
        )
        return list(res.scalars())

    async def detach_all_subtasks_from_section_parent(
        self, section_task_id: int
    ) -> int:
        subtasks = await self.list_subtasks_by_parent(section_task_id)
        if not subtasks:
            return 0
        for st in subtasks:
            st.parent_id = None
        self.session.add_all(subtasks)
        await self.session.flush()
        return len(subtasks)

    async def cascade_hard_delete_subtasks(self, parent_task_id: int) -> int:
        subtasks = await self.list_subtasks_by_parent(parent_task_id)
        for st in subtasks:
            await self.hard_delete_task(st)
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

    async def get_overall_task_statistics(self) -> dict:
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
            .join(Project, Project.id == Task.project_id)
            .where(
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

    async def unassign_user_from_task(
        self, *, target_user_id: int, task_id: int
    ) -> None:
        stmt = delete(TaskAssignee).where(
            TaskAssignee.user_id == target_user_id, TaskAssignee.task_id == task_id
        )
        await self.session.execute(stmt)
        await self.session.flush()

    async def is_user_member_of_task_project(
        self, task_id: int, user_id: int
    ) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(Task)
            .join(Project, Task.project_id == Project.id)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                Task.id == task_id,
                ProjectMember.user_id == user_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def is_task_in_active_project(self, task_id: int) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(Task)
            .join(Project, Task.project_id == Project.id)
            .where(
                # Pastikan di task sama
                Task.id == task_id,
                # Task berada di project yang aktif
                Project.status == StatusProject.ACTIVE,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def is_user_owner_of_tasks_project(
        self, user_id: int, task_id: int
    ) -> bool:
        result = await self.session.execute(
            select(1)
            .select_from(Task)
            .join(Project, Task.project_id == Project.id)
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                # memastikan id task sama
                Task.id == task_id,
                # memastikan user adalah anggota project
                ProjectMember.user_id == user_id,
                # memastikan user adalah owner project
                ProjectMember.role == RoleProject.OWNER,
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_project_member_user_ids_by_task(
        self, task_id: int
    ) -> Sequence[int]:
        """
        Mengambil daftar user_id yang menjadi anggota dari sebuah proyek.
        """
        stmt = (
            select(ProjectMember.user_id)
            .join(Task, Task.id == task_id)
            .where(Task.project_id == ProjectMember.project_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_report_summary_priority(self, project_id: int) -> dict[str, int]:
        completed = StatusTask.COMPLETED
        not_completed = [
            StatusTask.PENDING,
            StatusTask.IN_PROGRESS,
            StatusTask.CANCELLED,
        ]

        stmt = select(
            func.count(Task.id).label("total_task"),
            func.sum(case((Task.status == completed, 1), else_=0)).label(
                "task_complete"
            ),
            func.sum(case((Task.status.in_(not_completed), 1), else_=0)).label(
                "task_not_complete"
            ),
            func.sum(case((Task.priority == PriorityLevel.HIGH, 1), else_=0)).label(
                "high"
            ),
            func.sum(
                case((Task.priority == PriorityLevel.MEDIUM, 1), else_=0)
            ).label("medium"),
            func.sum(case((Task.priority == PriorityLevel.LOW, 1), else_=0)).label(
                "low"
            ),
        ).where(Task.project_id == project_id)
        row = (await self.session.execute(stmt)).one()
        return {
            "total_task": row.total_task or 0,
            "task_complete": row.task_complete or 0,
            "task_not_complete": row.task_not_complete or 0,
            "high": row.high or 0,
            "medium": row.medium or 0,
            "low": row.low or 0,
        }

    async def get_report_assignee_stats(self, project_id: int) -> list[dict]:
        completed = StatusTask.COMPLETED
        not_completed = [
            StatusTask.PENDING,
            StatusTask.IN_PROGRESS,
            StatusTask.CANCELLED,
        ]

        stmt = (
            select(
                TaskAssignee.user_id.label("user_id"),
                func.sum(case((Task.status == completed, 1), else_=0)).label(
                    "task_complete"
                ),
                func.sum(case((Task.status.in_(not_completed), 1), else_=0)).label(
                    "task_not_complete"
                ),
            )
            .join(Task, Task.id == TaskAssignee.task_id)
            .where(Task.project_id == project_id)
            .group_by(TaskAssignee.user_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return [
            {
                "user_id": r.user_id,
                "task_complete": r.task_complete or 0,
                "task_not_complete": r.task_not_complete or 0,
            }
            for r in rows
        ]

    async def get_report_weekly_stats(
        self, project_id: int, start_day: date, end_day: date
    ) -> dict[date, tuple[int, int]]:
        completed = StatusTask.COMPLETED
        not_completed = [
            StatusTask.PENDING,
            StatusTask.IN_PROGRESS,
            StatusTask.CANCELLED,
        ]

        stamp_expr = func.date(
            func.coalesce(Task.updated_at, Task.created_at, func.now())
        )
        stmt = (
            select(
                stamp_expr.label("d"),
                func.sum(case((Task.status == completed, 1), else_=0)).label(
                    "task_complete"
                ),
                func.sum(case((Task.status.in_(not_completed), 1), else_=0)).label(
                    "task_not_complete"
                ),
            )
            .where(
                Task.project_id == project_id,
                stamp_expr >= start_day,
                stamp_expr <= end_day,
            )
            .group_by(stamp_expr)
        )
        rows = (await self.session.execute(stmt)).all()
        return {r.d: (r.task_complete or 0, r.task_not_complete or 0) for r in rows}
