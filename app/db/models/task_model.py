import datetime
from enum import StrEnum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import TimeStampMixin

if TYPE_CHECKING:
    from app.db.models.attachment_model import Attachment
    from app.db.models.category_model import Category
    from app.db.models.comment_model import Comment
    from app.db.models.milestone_model import Milestone
    from app.db.models.project_model import Project
    from app.db.models.task_assigne_model import TaskAssignee


class ResourceType(StrEnum):
    TASK = "task"
    MILESTONE = "milestone"


class StatusTask(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class PriorityLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Task(Base, TimeStampMixin):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """ID tugas."""

    milestone_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("milestone.id"), nullable=False
    )
    """ID mileston"""

    name: Mapped[str] = mapped_column(Text, nullable=False)
    """Nama tugas."""

    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Deskripsi tugas."""

    status: Mapped[StatusTask] = mapped_column(
        Enum(StatusTask, name="status_task"), nullable=True
    )
    """Status tugas."""

    priority: Mapped[PriorityLevel | None] = mapped_column(
        Enum(PriorityLevel, name="priority_level"), nullable=True
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

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id", ondelete="CASCADE"), nullable=False
    )
    """ID proyek tempat tugas ini berada."""

    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("task.id", ondelete="CASCADE"), nullable=True
    )
    """ID tugas induk jika tugas ini merupakan sub-tugas."""

    category_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("category.id", ondelete="SET NULL"), nullable=True
    )

    # Relasi
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    """
    Relasi ke proyek yang terkait dengan tugas ini,
    relasi ini bersifat one to one (satu tugas hanya dapat terkait dengan satu
    proyek)
    """

    parent: Mapped[Optional["Task"]] = relationship(
        "Task", remote_side=[id], back_populates="sub_tasks"
    )
    """
    Relasi ke tugas induk jika tugas ini merupakan sub-tugas,
    relasi ini bersifat one to many (satu tugas induk dapat memiliki banyak
    sub-tugas)
    """

    sub_tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="parent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    """
    Relasi ke sub-tugas jika tugas ini merupakan tugas induk,
    relasi ini bersifat one to many (satu tugas induk dapat memiliki
    banyak sub-tugas)
    """

    assignees: Mapped[List["TaskAssignee"]] = relationship(
        "TaskAssignee",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    """
    Relasi ke pengguna yang ditugaskan untuk tugas ini,
    relasi ini bersifat one to many (satu tugas dapat ditugaskan kepada banyak
    pengguna)
    """

    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    """
    Relasi ke komentar yang dibuat untuk tugas ini,
    relasi ini bersifat one to many (satu tugas dapat memiliki banyak komentar)
    """

    attachments: Mapped[List["Attachment"]] = relationship(
        "Attachment",
        back_populates="task",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    """
    Relasi ke lampiran yang dibuat untuk tugas ini,
    relasi ini bersifat one to many (satu tugas dapat memiliki banyak lampiran)
    """

    milestone: Mapped["Milestone"] = relationship(
        "Milestone", back_populates="tasks"
    )
    """
    Relasi ke milestone yang terkait dengan tugas ini,
    relasi ini bersifat one to many (satu milestone dapat memiliki banyak tugas)
    """

    category: Mapped[Optional["Category"]] = relationship(
        "Category", back_populates="tasks"
    )
    """
    Relasi ke kategori yang terkait dengan tugas ini,
    relasi ini bersifat one to many (satu kategori dapat memiliki banyak tugas)
    """
