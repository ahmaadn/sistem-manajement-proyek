from app.schemas.base import BaseSchema


class UserInfo(BaseSchema):
    user_id: int
    data_pegawai_id: int
    nama: str
    role: str
    jabatan: str
    unit_kerja: str
