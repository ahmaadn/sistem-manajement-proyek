from datetime import date, timedelta
from typing import TYPE_CHECKING, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.role_model import Role
from app.db.repositories.dashboard_repository import (
    DashboardSQLAlchemyReadRepository,
    InterfaceDashboardReadRepository,
)
from app.schemas.dashboard import (
    AdminDashboardResponse,
    PMDashboardResponse,
    ProjectStatusSummary,
    UpcomingDeadlineItem,
    UserDashboardResponse,
    YearlySummary,
)
from app.schemas.task import TaskRead
from app.schemas.user import UserProjectStats

if TYPE_CHECKING:
    from app.services.project_service import ProjectService
    from app.services.task_service import TaskService
    from app.services.user_service import UserService


class DashboardService:
    def __init__(
        self,
        repo: Union[InterfaceDashboardReadRepository, AsyncSession],
    ) -> None:
        if isinstance(repo, AsyncSession):
            self.repo: InterfaceDashboardReadRepository = (
                DashboardSQLAlchemyReadRepository(repo)
            )
        else:
            self.repo = repo

    async def admin_dashboard(
        self, user_service: "UserService", limit: int
    ) -> AdminDashboardResponse:
        """Get admin dashboard data."""
        users = await user_service.list_user()
        role_counts = dict.fromkeys(Role, 0)
        for user in users:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
        top_users = sorted(users, key=lambda u: u.name, reverse=True)[:limit]
        return AdminDashboardResponse(top_users=top_users, role_counts=role_counts)

    async def pm_dashboard(
        self,
        user_id: int,
        project_service: "ProjectService",
        skip_deadline: int = 0,
        limit_deadline: int = 5,
    ) -> PMDashboardResponse:
        """Dashboard PM: ringkasan status, yearly summary, upcoming deadlines."""
        today = date.today()
        start_of_this_month = today.replace(day=1)
        one_year_ago = today - timedelta(days=365)

        summary = await self.repo.get_pm_project_status_summary(
            user_id=user_id, start_of_this_month=start_of_this_month
        )
        yearly_rows = await self.repo.get_pm_yearly_summary(
            user_id=user_id, one_year_ago=one_year_ago
        )
        upcoming_deadlines_rows = await self.repo.list_upcoming_project_deadlines(
            user_id=user_id, skip=skip_deadline, limit=limit_deadline
        )
        upcoming_deadlines = [
            UpcomingDeadlineItem(
                id=project.id,
                title=project.title,
                end_date=project.end_date,
                start_date=project.start_date,
                status=project.status,
                task_count=task_count,
                task_in_progress=task_in_progress,
            )
            for (project, task_count, task_in_progress) in upcoming_deadlines_rows
        ]

        return PMDashboardResponse(
            project_summary=ProjectStatusSummary(
                total_project=summary["total_project"],
                active_projects=summary["active_projects"],
                completed_projects=summary["completed_projects"],
                new_this_month=summary["new_this_month"],
            ),
            yearly_summary=[
                YearlySummary(
                    month=row["month"],
                    created_count=row["created_count"],
                    actived_count=row["actived_count"],
                    completed_count=row["completed_count"],
                )
                for row in yearly_rows
            ],
            upcoming_deadlines=upcoming_deadlines,
        )

    async def user_dashboard(
        self,
        user_id: int,
        task_service: "TaskService",
        project_service: "ProjectService",
        limit_tasks: int = 5,
    ) -> UserDashboardResponse:
        """Dashboard User: ringkasan project & tugas, upcoming tasks."""
        project_stats = await project_service.get_user_project_statistics(user_id)
        task_stats = await task_service.get_user_task_statistics(user_id)

        project_summary = UserProjectStats(
            total_project=project_stats.get("total_project", 0),
            project_active=project_stats.get("project_active", 0),
            project_completed=project_stats.get("project_completed", 0),
            total_task=task_stats.get("total_task", 0),
            task_in_progress=task_stats.get("task_in_progress", 0),
            task_completed=task_stats.get("task_completed", 0),
            task_cancelled=task_stats.get("task_cancelled", 0),
        )
        _upcoming_task_models = await self.repo.list_user_upcoming_tasks(
            user_id=user_id, limit=limit_tasks
        )

        # cast ke type SimpleTaskResponse
        upcoming_tasks: list[TaskRead] = [
            TaskRead.model_validate(t, from_attributes=True)
            for t in _upcoming_task_models
        ]

        return UserDashboardResponse(
            project_summary=project_summary,
            upcoming_tasks=upcoming_tasks,
        )
