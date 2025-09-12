from pydantic import Field

from app.db.models.project_member_model import RoleProject
from app.db.models.role_model import Role
from app.schemas.base import BaseSchema


class UserBase(BaseSchema):
    id: int = Field(..., description="ID pengguna")
    name: str = Field(..., description="Nama pengguna")
    employee_role: str = Field(..., description="Jabatan pengguna")
    email: str = Field(..., description="Email pengguna")
    position: str = Field(..., description="Posisi pengguna")
    profile_url: str = Field(..., description="URL profil pengguna")


class User(UserBase):
    role: Role = Field(
        ..., description="Peran pengguna di aplikasi sistem manajemen proyek"
    )


class UserProjectStats(BaseSchema):
    total_project: int = Field(0, description="Total proyek yang diikuti pengguna")
    project_active: int = Field(
        0, description="Jumlah proyek aktif yang diikuti pengguna"
    )
    project_completed: int = Field(
        0, description="Jumlah proyek selesai yang diikuti pengguna"
    )
    total_task: int = Field(0, description="Total tugas yang diikuti pengguna")
    task_in_progress: int = Field(
        0, description="Jumlah tugas aktif yang diikuti pengguna"
    )
    task_completed: int = Field(
        0, description="Jumlah tugas selesai yang diikuti pengguna"
    )
    task_cancelled: int = Field(
        0, description="Jumlah tugas dibatalkan yang diikuti pengguna"
    )


class ProjectParticipation(BaseSchema):
    project_id: int = Field(..., description="ID proyek")
    project_name: str = Field(..., description="Nama proyek")
    user_role: RoleProject = Field(..., description="Peran pengguna dalam proyek")


class UserDetail(User):
    statistics: UserProjectStats = Field(
        ..., description="Statistik proyek pengguna"
    )
    # projects: list[ProjectParticipant] = Field(
    #     default_factory=list, description="Daftar proyek yang diikuti pengguna"
    # )
