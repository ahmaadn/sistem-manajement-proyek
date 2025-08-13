from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import SoftDeleteMixin, TimeStampMixin

if TYPE_CHECKING:
    from app.db.models.task_model import Task


class StatusProject(StrEnum):
    TENDER = "tender"
    ACTIVE = "active"
    FINISH = "completed"
    CANCEL = "cancel"


class Project(Base, TimeStampMixin, SoftDeleteMixin):
    __tablename__ = "project"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """ID proyek."""

    title: Mapped[str] = mapped_column(Text, nullable=False)
    """Judul proyek."""

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Deskripsi proyek."""

    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(True), nullable=True
    )
    """Tanggal mulai proyek."""

    end_date: Mapped[datetime | None] = mapped_column(DateTime(True), nullable=True)
    """Tanggal selesai proyek."""

    status: Mapped[StatusProject] = mapped_column(
        Enum(StatusProject, name="status_project"),
        default=StatusProject.TENDER,
        nullable=False,
    )
    """Status proyek."""

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    """Dibuat oleh pengguna dengan ID tertentu."""

    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project")
    """
    Daftar tugas yang terkait dengan proyek ini.
    relasi one to many (satu proyek memiliki banyak tugas)
    """
