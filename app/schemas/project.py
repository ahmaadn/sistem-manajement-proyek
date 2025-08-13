import datetime

from pydantic import Field

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
    owner_id: int = Field(..., description="ID pembuat proyek")
