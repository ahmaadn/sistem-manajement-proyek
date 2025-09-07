from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.project_model import Project
    from app.db.models.task_model import Task


class Category(Base):
    __tablename__ = "category"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    """
    ID kategori
    """

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("project.id"), index=True
    )
    """
    ID proyek yang terkait dengan kategori ini
    """
    name: Mapped[str] = mapped_column(String)
    """
    Nama kategori
    """

    description: Mapped[str | None] = mapped_column(String, nullable=True)
    """
    Deskripsi kategori
    """

    tasks: Mapped[list["Task"]] = relationship("Task", back_populates="category")
    """
    Relasi ke tugas yang terkait dengan kategori ini,
    relasi ini bersifat one to many (satu kategori dapat memiliki banyak tugas)
    """

    project: Mapped["Project"] = relationship("Project", back_populates="categories")
    """
    Relasi ke proyek yang terkait dengan kategori ini,
    relasi ini bersifat many to one (banyak kategori dapat terkait dengan satu
    proyek)
    """
