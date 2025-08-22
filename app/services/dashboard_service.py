from datetime import date, timedelta
from typing import TYPE_CHECKING

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.project_model import Project, StatusProject
from app.db.models.role_model import Role
from app.schemas.dashboard import (
    AdminDashboardResponse,
    PMDashboardResponse,
    ProjectStatusSummary,
    YearlySummary,
)

if TYPE_CHECKING:
    from app.services.project_service import ProjectService
    from app.services.user_service import UserService


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def admin_dashboard(
        self, user_service: "UserService", limit: int
    ) -> AdminDashboardResponse:
        """Get admin dashboard data.

        Args:
            user_service (UserService): User service instance.
            limit (int): Limit for top users.

        Returns:
            AdminDashboardResponse: Admin dashboard response.
        """

        users = await user_service.list_user()
        role_counts = dict.fromkeys(Role, 0)

        for user in users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1

        top_users = sorted(users, key=lambda u: u.name, reverse=True)[:limit]

        return AdminDashboardResponse(top_users=top_users, role_counts=role_counts)

    async def pm_dashboard(
        self,
        project_service: "ProjectService",
        skip_deadline: int = 0,
        limit_deadline: int = 5,
    ):
        """Mendapatkan data dashboard untuk Project Manager.

        Args:
            project_service (ProjectService): Service untuk mengelola project.
            skip_deadline (int, optional): Jumlah deadline yang dilewati.
                Defaults to 0.
            limit_deadline (int, optional): Batas jumlah deadline yang ditampilkan.
                Defaults to 5.

        Returns:
            PMDashboardResponse: Data dashboard untuk Project Manager.
        """

        today = date.today()
        start_of_this_month = today.replace(day=1)

        # Semua project di dapatkan, walaupun pm bukan owner dari project
        stmt = select(
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
        ).where(
            Project.deleted_at.is_(None),
        )

        current_stats = await self.session.execute(stmt)
        current_stats = current_stats.fetchone()

        # Statistik per bulan dalam 1 tahun
        one_year_ago = today - timedelta(days=365)

        created_q = (
            select(
                func.date_trunc("month", Project.created_at).label("month"),
                func.sum(
                    case((Project.created_at >= one_year_ago, 1), else_=0)
                ).label("created_count"),
                func.sum(
                    case((Project.status == StatusProject.COMPLETED, 1), else_=0)
                ).label("completed_count"),
            )
            .where(Project.created_at >= one_year_ago)
            .group_by("month")
        )

        yearly_summary = await self.session.execute(created_q)
        yearly_summary = yearly_summary.fetchall()

        upcoming_deadlines = await project_service.list(
            skip=skip_deadline,
            limit=limit_deadline,
            filters={"status": StatusProject.ACTIVE},
            custom_query=lambda q: q.order_by(Project.end_date),
        )

        return PMDashboardResponse(
            project_summary=ProjectStatusSummary(
                total_project=current_stats.total_project or 0,
                active_projects=current_stats.active_projects or 0,
                completed_projects=current_stats.completed_projects or 0,
                new_this_month=current_stats.new_this_month or 0,
            ),
            yearly_summary=[
                YearlySummary(
                    month=row.month,
                    created_count=row.created_count,
                    completed_count=row.completed_count,
                )
                for row in yearly_summary
            ],
            upcoming_deadlines=upcoming_deadlines,
        )
