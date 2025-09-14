import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import CreateStampMixin

if TYPE_CHECKING:
    from app.db.models.project_model import Project
    from app.db.models.task_model import Task


class NotificationType(StrEnum):
    PROJECT_DONE = "project_done"


class Notification(Base, CreateStampMixin):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True, nullable=False
    )
    """ID notifikasi unik."""

    recipient_id: Mapped[int] = mapped_column(Integer, nullable=False)
    """ID pengguna penerima notifikasi."""

    actor_id: Mapped[int] = mapped_column(Integer, nullable=False)
    """ID pengguna yang melakukan aksi pemicu notifikasi."""

    project_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    """ID proyek terkait notifikasi."""

    task_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("task.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    """ID tugas terkait notifikasi."""

    type: Mapped[str] = mapped_column(String(50), nullable=False)
    """Tipe notifikasi."""

    message: Mapped[str] = mapped_column(String(), nullable=False)
    """Pesan notifikasi."""

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """Status apakah notifikasi sudah dibaca atau belum."""

    read_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    """Waktu ketika notifikasi dibaca."""

    project: Mapped["Project"] = relationship(
        "Project", back_populates="notifications"
    )
    """
    Proyek terkait notifikasi. Relasi bersifat one-to-one (1 notifikasi hanya 1
    proyek).
    """

    task: Mapped["Task"] = relationship("Task", back_populates="notifications")
    """
    Task terkait notifikasi. Relasi bersifat one-to-one (1 notifikasi hanya 1 task).
    """
