from __future__ import annotations

from datetime import date
from typing import Protocol

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.models.project_model import Project, StatusProject
from app.db.models.task_assigne_model import TaskAssignee
from app.db.models.task_model import StatusTask, Task


class InterfaceDashboardReadRepository(Protocol):
    async def get_pm_project_status_summary(
        self, *, user_id: int, start_of_this_month: date
    ) -> dict:
        """Mendapatkan ringkasan status proyek untuk PM.

        Args:
            start_of_this_month (date): Tanggal awal bulan ini.

        Returns:
            dict: Ringkasan status proyek. terdiri dari total_project (Jumlah proyek)
            , active_projects (Jumlah proyek aktif), completed_projects (Jumlah
            proyek selesai), dan new_this_month (Jumlah proyek baru bulan ini).
        """
        ...

    async def get_pm_yearly_summary(
        self, *, user_id: int, one_year_ago: date
    ) -> list[dict]:
        """Mendapatkan ringkasan tahunan untuk PM.

        Args:
            one_year_ago (date): Tanggal satu tahun yang lalu.

        Returns:
            list[dict]: Daftar ringkasan tahunan. terdiri dari bulan (month), jumlah
            proyek yang dibuat (created_count), diaktifkan (actived_count), dan
            diselesaikan (completed_count).
        """
        ...

    async def list_upcoming_project_deadlines(
        self, *, user_id: int, skip: int, limit: int
    ) -> list[tuple[Project, int, int]]:
        """List proyek yang akan datang berdasarkan tenggat waktu untuk PM.

        Args:
            user_id (int): ID pengguna.
            skip (int): Jumlah proyek yang dilewati.
            limit (int): Jumlah proyek yang diambil.

        Returns:
            list[tuple[Project, int, int]]: Daftar proyek yang akan datang. key
                terdiri dari 'project', 'task_count', 'task_in_progress'.
        """
        ...

    async def list_user_upcoming_tasks(self, user_id: int, limit: int) -> list[Task]:
        """List tugas yang akan datang untuk pengguna tertentu.

        Args:
            user_id (int): ID pengguna.
            limit (int): Jumlah tugas yang diambil.

        Returns:
            list[Task]: Daftar tugas yang akan datang untuk pengguna tertentu.
        """
        ...


class DashboardSQLAlchemyReadRepository(InterfaceDashboardReadRepository):
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_pm_project_status_summary(
        self, *, user_id: int, start_of_this_month: date
    ) -> dict:
        stmt = (
            select(
                func.count(Project.id).label("total_project"),
                func.sum(
                    case((Project.status == StatusProject.ACTIVE, 1), else_=0)
                ).label("active_projects"),
                func.sum(
                    case((Project.status == StatusProject.COMPLETED, 1), else_=0)
                ).label("completed_projects"),
                func.sum(
                    case((Project.created_at >= start_of_this_month, 1), else_=0)
                ).label("new_this_month"),
            )
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                # Project yang tidak dihapus
                Project.deleted_at.is_(None),
                # Filter bedasarkan owner
                ProjectMember.user_id == user_id,
                # Filter berdasarkan role
                ProjectMember.role == RoleProject.OWNER,
            )
        )

        res = await self.session.execute(stmt)
        row = res.fetchone()
        return {
            "total_project": (row.total_project or 0) if row else 0,
            "active_projects": (row.active_projects or 0) if row else 0,
            "completed_projects": (row.completed_projects or 0) if row else 0,
            "new_this_month": (row.new_this_month or 0) if row else 0,
        }

    async def get_pm_yearly_summary(
        self, *, user_id: int, one_year_ago: date
    ) -> list[dict]:
        q = (
            select(
                # bulan proyek dibuat
                func.date_trunc("month", Project.created_at).label("month"),
                # jumlah project yang dibuat dalam bulan tersebut
                func.sum(
                    case((Project.created_at >= one_year_ago, 1), else_=0)
                ).label("created_count"),
                # jumlah project ACTIVE
                func.sum(
                    case((Project.status == StatusProject.ACTIVE, 1), else_=0)
                ).label("actived_count"),
                # jumlah project COMPLETED
                func.sum(
                    case((Project.status == StatusProject.COMPLETED, 1), else_=0)
                ).label("completed_count"),
            )
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                # proyek yang dibuat dalam satu tahun terakhir
                Project.created_at >= one_year_ago,
                # proyek yang bukan di hapus
                Project.deleted_at.is_(None),
                # Filter bedasarkan owner
                ProjectMember.user_id == user_id,
                # Filter berdasarkan role
                ProjectMember.role == RoleProject.OWNER,
            )
            .group_by("month")
        )
        res = await self.session.execute(q)
        return [
            {
                "month": row.month,
                "created_count": row.created_count,
                "actived_count": row.actived_count,
                "completed_count": row.completed_count,
            }
            for row in res.fetchall()
        ]

    async def list_upcoming_project_deadlines(
        self, *, user_id: int, skip: int, limit: int
    ):
        q = (
            select(
                Project,
                # Hitung jumlah task per status berdasarkan corelasi subquery
                (
                    select(func.count())
                    .where(
                        Task.project_id == Project.id,
                        Task.deleted_at.is_(None),
                        Task.status != StatusTask.PENDING,
                    )
                    .scalar_subquery()
                ).label("task_count"),
                (
                    select(func.count())
                    .where(
                        Task.project_id == Project.id,
                        Task.deleted_at.is_(None),
                        Task.status == StatusTask.IN_PROGRESS,
                    )
                    .scalar_subquery()
                ).label("task_in_progress"),
            )
            .join(ProjectMember, ProjectMember.project_id == Project.id)
            .where(
                # Project yang tidak dihapus
                Project.deleted_at.is_(None),
                # Project yang aktif
                Project.status == StatusProject.ACTIVE,
                # Project yang memiliki end date
                Project.end_date.is_not(None),
                # Filter bedasarkan owner
                ProjectMember.user_id == user_id,
                # Filter berdasarkan role
                ProjectMember.role == RoleProject.OWNER,
            )
            .order_by(Project.end_date.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(q)
        rows = res.all()
        return [
            (row[0], int(row.task_count or 0), int(row.task_in_progress or 0))
            for row in rows
        ]

    async def list_user_upcoming_tasks(self, user_id: int, limit: int) -> list[Task]:
        q = (
            select(Task)
            .join(TaskAssignee, TaskAssignee.task_id == Task.id)
            .join(Project, Project.id == Task.project_id)
            .where(
                # user yang di assign
                TaskAssignee.user_id == user_id,
                # task tidak di hapus
                Task.deleted_at.is_(None),
                # proyek yang tidak di hapus
                Project.deleted_at.is_(None),
                # proyek yang aktif
                Project.status == StatusProject.ACTIVE,
                # task yang memiliki due date
                Task.due_date.is_not(None),
                # task yang tidak di selesaikan
                Task.status != StatusTask.COMPLETED,
            )
            .order_by(
                case((Task.due_date < func.now(), 0), else_=1),
                Task.due_date.asc(),
            )
            .limit(limit)
        )
        res = await self.session.execute(q)
        return list(res.scalars().all())
