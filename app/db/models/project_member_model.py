from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import TimeStampMixin

if TYPE_CHECKING:
    from app.db.models.project_model import Project


class RoleProject(StrEnum):
    OWNER = "owner"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class ProjectMember(Base, TimeStampMixin):
    __tablename__ = "project_member"

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id"), primary_key=True, autoincrement=False
    )
    """ID proyek"""

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    """ID pengguna"""

    role: Mapped[RoleProject] = mapped_column(Enum(RoleProject, name="role_project"))
    """Role anggota proyek"""

    # Relasi
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    """Relasi ke Project. relasi bersifat many-to-one"""
