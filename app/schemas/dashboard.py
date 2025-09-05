from datetime import datetime

from app.db.models.project_model import StatusProject
from app.db.models.role_model import Role
from app.schemas.base import BaseSchema
from app.schemas.task import TaskRead
from app.schemas.user import User, UserProjectStats


class AdminDashboardResponse(BaseSchema):
    top_users: list[User]
    role_counts: dict[Role, int]


class ProjectStatusSummary(BaseSchema):
    total_project: int
    active_projects: int
    completed_projects: int
    new_this_month: int


class YearlySummary(BaseSchema):
    month: datetime
    created_count: int
    actived_count: int
    completed_count: int


class UpcomingDeadlineItem(BaseSchema):
    id: int
    title: str
    start_date: datetime | None
    end_date: datetime | None
    status: StatusProject
    task_count: int
    task_in_progress: int


class PMDashboardResponse(BaseSchema):
    project_summary: ProjectStatusSummary
    yearly_summary: list[YearlySummary]
    upcoming_deadlines: list[UpcomingDeadlineItem]


class UserDashboardResponse(BaseSchema):
    project_summary: UserProjectStats
    upcoming_tasks: list[TaskRead]
