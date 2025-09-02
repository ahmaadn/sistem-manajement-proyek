from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import CreateStampMixin

if TYPE_CHECKING:
    from app.db.models.comment_model import Comment
    from app.db.models.task_model import Task


class Attachment(Base, CreateStampMixin):
    __tablename__ = "attachment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    """
    ID lampiran
    """

    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    """
    ID pengguna yang melampirkan file
    """

    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("task.id"), nullable=False
    )
    """
    ID tugas yang dilampirkan
    """

    comment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("comment.id"), nullable=True
    )

    """
    ID komentar yang dilampirkan. Bisa null jika tidak lampiran terkait komentar.
    """

    file_name: Mapped[str] = mapped_column(String, nullable=False)
    """
    Nama file lampiran
    """

    file_path: Mapped[str] = mapped_column(String, nullable=False)
    """
    Path file lampiran
    """

    file_size: Mapped[str] = mapped_column(String, nullable=False)
    """
    Ukuran file lampiran. Dalam satuan byte.
    """

    mime_type: Mapped[str] = mapped_column(String, nullable=False)
    """
    Tipe MIME dari lampiran.
    """

    task: Mapped["Task"] = relationship("Task", back_populates="attachments")
    """
    Tugas yang dilampirkan. relasi bersifat Many to one. beberapa lampiran hanya bisa
    terkait dengan 1 tugas.
    """

    comment: Mapped["Comment"] = relationship(
        "Comment", back_populates="attachments"
    )
    """
    Relasi dengan komentar. relasi bersifat one-to-many. 1 komentar bisa banyak
    lampiran
    """
