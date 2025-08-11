from datetime import datetime

from app.db.models.proyek_model import StatusProyek
from app.schemas.base import BaseSchema


class ProyekCreate(BaseSchema):
    nama: str
    deskripsi: str
    status: StatusProyek


class ProyekResponse(BaseSchema):
    id: int
    nama: str
    deskripsi: str
    status: StatusProyek
    author_id: int
    created_at: datetime
    updated_at: datetime


class ProyekUpdate(BaseSchema):
    nama: str | None = None
    deskripsi: str | None = None
    status: StatusProyek | None = None
