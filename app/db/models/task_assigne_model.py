from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.task_model import Task


class TaskAssignee(Base):
    __tablename__ = "task_assignee"

    task_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("task.id", ondelete="CASCADE"),
        primary_key=True,
        autoincrement=False,
    )
    """
    ID tugas yang ditugaskan kepada pengguna.
    """

    user_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=False
    )
    """
    ID pengguna yang ditugaskan untuk tugas.
    """

    task: Mapped["Task"] = relationship("Task", back_populates="assignees")
    """
    Relasi ke tugas yang ditugaskan kepada pengguna. many to one
    """
