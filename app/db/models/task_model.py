import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import SoftDeleteMixin, TimeStampMixin

if TYPE_CHECKING:
    from app.db.models.project_model import Project


class ResourceType(StrEnum):
    TASK = "task"
    MILESTONE = "milestone"
    SECTION = "section"


class StatusTask(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PriorityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base, TimeStampMixin, SoftDeleteMixin):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """ID tugas."""

    name: Mapped[str] = mapped_column(Text, nullable=False)
    """Nama tugas."""

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Deskripsi tugas."""

    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, name="resource_type"),
        default=ResourceType.TASK,
        nullable=False,
    )
    """Tipe sumber daya tugas."""

    status: Mapped[StatusTask] = mapped_column(
        Enum(StatusTask, name="status_task"),
        default=StatusTask.PENDING,
        nullable=False,
    )
    """Status tugas."""

    priority: Mapped[PriorityLevel] = mapped_column(
        Enum(PriorityLevel, name="priority_level"),
        default=PriorityLevel.MEDIUM,
        nullable=False,
    )
    """Tipe sumber daya tugas."""

    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    """Urutan tampilan tugas."""

    due_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), nullable=True
    )
    """Tanggal jatuh tempo tugas."""

    start_date: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), nullable=True
    )
    """Tanggal mulai pengerjaan tugas."""

    estimated_duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Estimasi waktu pengerjaan dalam satuan menit."""

    total_time_logged: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Total waktu yang dicatat dalam satuan menit."""

    created_by: Mapped[int] = mapped_column(Integer, nullable=False)
    """ID pengguna yang membuat tugas."""

    assigned_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """ID pengguna yang ditugaskan untuk tugas."""

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id"), nullable=False
    )

    """ID proyek tempat tugas ini berada."""

    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task.id"), nullable=True
    )
    """ID tugas induk jika tugas ini merupakan sub-tugas."""

    # Relasi
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    """
    Relasi ke proyek yang terkait dengan tugas ini,
    relasi ini bersifat one to one (satu tugas hanya dapat terkait dengan satu proyek)
    """

    parent: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side=[id], back_populates="sub_tasks"
    )
    """
    Relasi ke tugas induk jika tugas ini merupakan sub-tugas,
    relasi ini bersifat one to many (satu tugas induk dapat memiliki banyak
    sub-tugas)
    """

    sub_tasks: Mapped[List["Task"]] = relationship("Task", back_populates="parent")
    """
    Relasi ke sub-tugas jika tugas ini merupakan tugas induk,
    relasi ini bersifat one to many (satu tugas induk dapat memiliki
    banyak sub-tugas)
    """
