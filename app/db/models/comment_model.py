from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import CreateStampMixin

if TYPE_CHECKING:
    from app.db.models.task_model import Task


class Comment(Base, CreateStampMixin):
    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, unique=True
    )
    """ID komentar"""

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task.id"), nullable=False
    )
    """ID task yang dikomentari"""

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    """ID pengguna yang membuat komentar"""

    content: Mapped[str] = mapped_column(Text, nullable=False)
    """Content pesan"""

    task: Mapped["Task"] = relationship("Task", back_populates="comment")
    """
    Relasi dengan task. relasi bersifat one to one. 1 comment hanya bisa dimiliki
    oleh 1 task.
    """
