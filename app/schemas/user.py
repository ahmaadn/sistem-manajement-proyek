from pydantic import Field

from app.db.models.role_model import Role
from app.schemas.base import BaseSchema


class UserProfile(BaseSchema):
    id: int = Field(..., description="ID pengguna")
    name: str = Field(..., description="Nama pengguna")
    employee_role: str = Field(..., description="Jabatan pengguna")
    email: str = Field(..., description="Email pengguna")
    username: str = Field(..., description="Username pengguna")
    position: str = Field(..., description="Posisi pengguna")
    work_unit: str = Field(..., description="Unit kerja pengguna")
    address: str = Field(..., description="Alamat pengguna")


class UserRead(UserProfile):
    role: Role = Field(
        ..., description="Peran pengguna di aplikasi sistem manajemen proyek"
    )
