from pydantic import Field

from app.db.models.project_member_model import RoleProject
from app.schemas.base import BaseSchema


class ProjectMemberAdd(BaseSchema):
    user_id: int = Field(
        ..., description="ID pengguna yang akan ditambahkan sebagai anggota proyek"
    )
    role: RoleProject = Field(
        default=RoleProject.CONTRIBUTOR, description="Peran anggota proyek"
    )


class ProjectMemberRoleUpdate(BaseSchema):
    role: RoleProject = Field(..., description="Peran baru anggota proyek")
