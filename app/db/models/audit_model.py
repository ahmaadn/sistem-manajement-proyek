from enum import StrEnum
from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import CreateStampMixin

if TYPE_CHECKING:
    from app.db.models.project_model import Project
    from app.db.models.task_model import Task


class AuditLog(Base, CreateStampMixin):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """ID unik untuk setiap entri audit log."""

    user_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    """ID pengguna yang terkait dengan audit log."""

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id"), nullable=True, default=None
    )
    """ID proyek yang terkait dengan audit log."""

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task.id"), nullable=True, default=None
    )
    """ID tugas yang terkait dengan audit log."""

    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    """Tipe aksi yang dicatat dalam audit log."""

    detail: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, nullable=True, server_default="{}"
    )
    """
    Detail log, detail dapat berisi informasi tambahan tentang perubahan yang
    dilakukan.
    """

    project: Mapped["Project"] = relationship("Project", back_populates="audit_logs")
    """
    Relasi ke Project.
    relasi bersifat one-to-one (1 audit log hanya 1 project)
    """

    task: Mapped["Task"] = relationship("Task", back_populates="audit_logs")
    """
    Relasi ke Task.
    relasi bersifat one-to-one (1 audit log hanya 1 task)
    """


class AuditEventType(StrEnum):
    # Task
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_REMOVED = "task_removed"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_DUE_DATE_CHANGED = "task_due_date_changed"
    TASK_PRIORITY_CHANGED = "task_priority_changed"
    TASK_TITLE_CHANGED = "task_title_changed"

    # Assign
    TASK_ASSIGNEE_ADDED = "task_assignee_added"
    TASK_ASSIGNEE_REMOVED = "task_assignee_removed"

    # Project
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_REMOVED = "project_removed"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
