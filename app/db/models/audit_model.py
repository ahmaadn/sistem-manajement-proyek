from typing import TYPE_CHECKING, Any, Dict

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import CreateStampMixin

if TYPE_CHECKING:
    from app.db.models.project_model import Project


class AuditLog(Base, CreateStampMixin):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    """ID unik untuk setiap entri audit log."""

    performed_by: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    """ID pengguna yang terkait dengan audit log."""

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("project.id", ondelete="CASCADE"),
        nullable=True,
        default=None,
    )
    """ID proyek yang terkait dengan audit log."""

    task_id: Mapped[int] = mapped_column(Integer, nullable=True, default=None)
    """ID tugas yang terkait dengan audit log."""

    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    """Tipe aksi yang dicatat dalam audit log."""

    details: Mapped[Dict[str, Any]] = mapped_column(
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
