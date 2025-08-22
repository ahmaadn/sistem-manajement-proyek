import datetime

from pydantic import Field

from app.db.models.project_member_model import RoleProject
from app.db.models.project_model import StatusProject
from app.schemas.base import BaseSchema


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


class ProjectResponse(BaseSchema):
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


class ProjectStatsResponse(BaseSchema):
    total_tasks: int = Field(
        default=0, description="Jumlah total tugas dalam proyek"
    )
    total_completed_tasks: int = Field(
        default=0, description="Jumlah tugas yang telah selesai"
    )
    total_milestones: int = Field(
        default=0, description="Jumlah milestone dalam proyek"
    )
    task_milestones_completed: int = Field(
        default=0, description="Jumlah milestone yang telah selesai"
    )


class ProjectMemberResponse(BaseSchema):
    user_id: int = Field(..., description="ID pengguna")
    name: str = Field(..., description="Nama pengguna")
    email: str = Field(..., description="Email pengguna")
    project_role: RoleProject = Field(..., description="Peran dalam proyek")


class ProjectDetailResponse(ProjectResponse):
    members: list[ProjectMemberResponse] = Field(
        default_factory=list, description="Anggota proyek"
    )

    stats: ProjectStatsResponse = Field(..., description="Statistik proyek")


class ProjectPublicResponse(ProjectResponse):
    project_role: RoleProject = Field(..., description="Peran dalam proyek")
