from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List

from sqlalchemy import DateTime, Enum, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import SoftDeleteMixin, TimeStampMixin

if TYPE_CHECKING:
    from app.db.models.audit_model import AuditLog
    from app.db.models.category_model import Category
    from app.db.models.milestone_model import Milestone
    from app.db.models.notification_model import Notification
    from app.db.models.project_member_model import ProjectMember
    from app.db.models.task_model import Task


class StatusProject(StrEnum):
    TENDER = "tender"
    ACTIVE = "active"
    COMPLETED = "completed"
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

    members: Mapped[List["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    """
    Daftar anggota proyek.
    relasi one to many (satu proyek memiliki banyak anggota)
    """

    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog", back_populates="project"
    )
    """
    Daftar log audit yang terkait dengan proyek ini.
    relasi one to many (satu proyek memiliki banyak log audit)
    """

    milestones: Mapped[List["Milestone"]] = relationship(
        "Milestone", back_populates="project"
    )
    """
    Daftar tonggak yang terkait dengan proyek ini.
    relasi one to many (satu proyek memiliki banyak tonggak)
    """

    categories: Mapped[List["Category"]] = relationship(
        "Category", back_populates="project", cascade="all, delete-orphan"
    )
    """
    Daftar kategori yang terkait dengan proyek ini.
    relasi one to many (satu proyek memiliki banyak kategori)
    """

    notifications: Mapped[List["Notification"]] = relationship(
        "Notification",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    """
    Daftar notifikasi yang terkait dengan proyek ini.
    relasi one to many (satu proyek memiliki banyak notifikasi)
    """
