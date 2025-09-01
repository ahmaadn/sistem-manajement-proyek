from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import TimeStampMixin

if TYPE_CHECKING:
    from app.db.models.project_model import Project
    from app.db.models.task_model import Task


class Milestone(Base, TimeStampMixin):
    __tablename__ = "milestone"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, unique=True, index=True, autoincrement=True
    )
    """
    ID unik untuk setiap milestone.
    """

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id"), nullable=False
    )
    """
    Relasi ke proyek yang terkait dengan milestone ini.
    """

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    """
    Judul milestone.
    """

    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    """
    Urutan tampilan milestone.
    """

    project: Mapped["Project"] = relationship("Project", back_populates="milestones")
    """
    Relasi ke proyek yang terkait dengan milestone ini.
    """

    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="milestone", cascade="all, delete-orphan"
    )
    """
    Relasi ke tugas yang terkait dengan milestone ini,
    relasi ini bersifat one to many (satu milestone dapat memiliki banyak tugas)
    """
