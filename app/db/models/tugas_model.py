import datetime
from enum import StrEnum
from typing import List, Optional
from uuid import UUID

from fastapi_utils.guid_type import GUID
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.models.mixin import SoftDeleteMixin, TimeStampMixin


class JenisTugasType(StrEnum):
    TUGAS = "tugas"
    SUB_TUGAS = "sub_tugas"
    MILESTONE = "milestone"
    APPROVAL = "approval"


class StatusPenyeelesaianType(StrEnum):
    TODO = "todo"
    DONE = "done"
    APPROVED = "approved"


class PrioritasType(StrEnum):
    TINGGI = "tinggi"
    SEDANG = "sedang"
    RENDAH = "rendah"


class Tugas(Base, TimeStampMixin, SoftDeleteMixin):
    __tablename__ = "tugas"

    id: Mapped[UUID] = mapped_column(GUID, primary_key=True)
    judul: Mapped[str] = mapped_column(String, nullable=False)
    deskripsi: Mapped[str | None] = mapped_column(
        String, nullable=True, default=None
    )
    tipe_sumber_daya: Mapped[JenisTugasType] = mapped_column(
        Enum(JenisTugasType), default=JenisTugasType.TUGAS, nullable=False
    )
    status_penyelesaian: Mapped[StatusPenyeelesaianType] = mapped_column(
        Enum(StatusPenyeelesaianType),
        default=StatusPenyeelesaianType.TODO,
        nullable=False,
    )
    prioritas: Mapped[PrioritasType] = mapped_column(
        Enum(PrioritasType), default=PrioritasType.RENDAH, nullable=False
    )
    urutan: Mapped[int] = mapped_column(Integer, nullable=False)
    tenggat_waktu: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), default=None, nullable=True
    )
    mulai_waktu: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), default=None, nullable=True
    )
    estimasi_waktu: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_waktu_tercatat: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Foreign Key
    create_by_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tugas_induk_id: Mapped[UUID | None] = mapped_column(
        GUID, ForeignKey("tugas.id"), nullable=True
    )
    proyek_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("proyek.id"), nullable=False
    )
    ditugaskan_ke: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationship
    # many to one
    proyek = relationship("Proyek", back_populates="tugas")

    # Relasi ke Tugas Induk (Many-to-One, self-referencing)
    tugas_induk: Mapped[Optional["Tugas"]] = relationship(
        remote_side=[id], back_populates="subtugas"
    )

    # Relasi ke banyak Subtugas (One-to-Many, self-referencing)
    subtugas: Mapped[List["Tugas"]] = relationship(
        back_populates="tugas_induk", cascade="all, delete-orphan"
    )
