import datetime

from pydantic import Field

from app.db.models.project_member_model import RoleProject
from app.db.models.project_model import StatusProject
from app.db.models.task_model import StatusTask
from app.schemas.base import BaseSchema
from app.schemas.pagination import PaginationSchema


class ProjectCreate(BaseSchema):
    title: str = Field(..., description="Judul proyek")
    description: str | None = Field(default=None, description="Deskripsi proyek")
    start_date: datetime.datetime | None = Field(
        default=None, description="Tanggal mulai proyek"
    )
    end_date: datetime.datetime | None = Field(
        default=None, description="Tanggal selesai proyek"
    )
    status: StatusProject = Field(
        default=StatusProject.TENDER, description="Status proyek"
    )


class ProjectUpdate(BaseSchema):
    title: str | None = Field(default=None, description="Judul proyek")
    description: str | None = Field(default=None, description="Deskripsi proyek")
    start_date: datetime.datetime | None = Field(
        default=None, description="Tanggal mulai proyek"
    )
    end_date: datetime.datetime | None = Field(
        default=None, description="Tanggal selesai proyek"
    )
    status: StatusProject | None = Field(default=None, description="Status proyek")


class ProjectRead(BaseSchema):
    id: int = Field(..., description="ID proyek")
    title: str = Field(..., description="Judul proyek")
    description: str | None = Field(default=None, description="Deskripsi proyek")
    start_date: datetime.datetime | None = Field(
        default=None, description="Tanggal mulai proyek"
    )
    end_date: datetime.datetime | None = Field(
        default=None, description="Tanggal selesai proyek"
    )
    status: StatusProject = Field(
        default=StatusProject.TENDER, description="Status proyek"
    )
    created_by: int = Field(..., description="ID pembuat proyek")


class ProjectStats(BaseSchema):
    total_tasks: int = Field(
        default=0, description="Jumlah total tugas dalam proyek"
    )
    total_completed_tasks: int = Field(
        default=0, description="Jumlah tugas yang telah selesai"
    )


class ProjectMemberRead(BaseSchema):
    user_id: int = Field(..., description="ID pengguna")
    name: str = Field(..., description="Nama pengguna")
    email: str = Field(..., description="Email pengguna")
    project_role: RoleProject = Field(..., description="Peran dalam proyek")
    profile_url: str | None = Field(
        default=None, description="URL foto profil pengguna"
    )


class ProjectDetail(ProjectRead):
    members: list[ProjectMemberRead] = Field(
        default_factory=list, description="Anggota proyek"
    )

    stats: ProjectStats = Field(..., description="Statistik proyek")


class ProjectSummary(BaseSchema):
    total_project: int = Field(..., description="Total proyek")
    project_active: int = Field(..., description="Proyek aktif")
    project_completed: int = Field(..., description="Proyek selesai")
    project_tender: int = Field(0, description="Proyek tender")
    project_cancel: int = Field(0, description="Proyek batal")


class ProjectPaginationItem(ProjectRead):
    total_tasks: int = Field(
        default=0, description="Jumlah total tugas dalam proyek"
    )


class ProjectListPage(PaginationSchema[ProjectPaginationItem]):
    summary: ProjectSummary = Field(..., description="Ringkasan proyek")


class ProjectReportSummary(BaseSchema):
    total_task: int
    task_complete: int
    task_not_complete: int


class ProjectReportAssignee(BaseSchema):
    user_id: int
    email: str
    profile_url: str
    task_complete: int
    task_not_complete: int


class ProjectReportPriority(BaseSchema):
    high: int
    medium: int
    low: int


class ProjectReportWeekItem(BaseSchema):
    date: datetime.date
    task_complete: int
    task_not_complete: int


class TaskEstimationItem(BaseSchema):
    task_id: int
    milestone_id: int
    name: str
    status: StatusTask | None = None
    finish_duration: int | None = None
    estimated_duration: int | None = None
    start_date: datetime.datetime | None = None
    due_date: datetime.datetime | None = None
    completed_at: datetime.datetime | None = None


class ProjectReport(BaseSchema):
    project_summary: ProjectReportSummary
    assignee: list[ProjectReportAssignee]
    priority: ProjectReportPriority
    weakly_report: list[ProjectReportWeekItem]
    tasks_estimation: list[TaskEstimationItem]
