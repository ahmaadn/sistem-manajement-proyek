from enum import StrEnum

from sqlalchemy import Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import SoftDeleteMixin, TimeStampMixin


class StatusProyek(StrEnum):
    TENDER = "tender"
    AKTIF = "aktif"
    SELESAI = "selesai"
    BATAL = "batal"


class Proyek(Base, TimeStampMixin, SoftDeleteMixin):
    __tablename__ = "proyek"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nama: Mapped[str] = mapped_column(String(100), nullable=False)
    deskripsi: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[StatusProyek] = mapped_column(
        Enum(StatusProyek), nullable=False, default=StatusProyek.TENDER
    )
    created_by_id: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationship
    # one to many
    tugas = relationship("Tugas", back_populates="proyek")
