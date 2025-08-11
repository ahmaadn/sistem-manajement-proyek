from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.proyek_manager import ProyekManager, get_proyek_manager
from app.db.models.proyek_model import Proyek
from app.schemas.proyek import ProyekCreate, ProyekResponse, ProyekUpdate
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["Proyek"])


@cbv(r)
class _Proyek:
    proyek_manager: ProyekManager = Depends(get_proyek_manager)

    def __init__(self) -> None:
        self.session = self.proyek_manager.session

    @r.post(
        "/proyek",
        status_code=status.HTTP_201_CREATED,
        response_model=ProyekResponse,
        responses={
            status.HTTP_201_CREATED: {
                "description": "proyek berhasil dibuat",
                "model": ProyekResponse,
            }
        },
    )
    async def create_proyek(self, proyek: ProyekCreate):
        proyek_item = await self.proyek_manager.create(1, proyek)
        return self._map_proyek_to_response(proyek_item)

    @r.put(
        "/proyek/{proyek_id}",
        status_code=status.HTTP_200_OK,
        response_model=ProyekResponse,
        responses={
            status.HTTP_200_OK: {
                "description": "Proyek berhasil diperbarui",
                "model": ProyekResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def update_proyek(self, proyek_id: int, proyek: ProyekUpdate):
        """memperbarui proyek"""
        proyel_item = await self.proyek_manager.update(proyek_id, proyek)
        return self._map_proyek_to_response(proyel_item)

    @r.delete(
        "/proyek/{proyek_id}",
        status_code=status.HTTP_202_ACCEPTED,
        responses={
            status.HTTP_202_ACCEPTED: {
                "description": "Proyek berhasil dihapus",
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Proyek tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def delete_proyek(self, proyek_id: int):
        """menghapus proyek"""

        await self.proyek_manager.delete(proyek_id)

    def _map_proyek_to_response(self, proyek: Proyek) -> ProyekResponse:
        """
        Mengonversi objek Proyek menjadi objek ProyekResponse.

        Args:
            proyek (Proyek): Objek proyek yang akan dikonversi.

        Returns:
            ProyekResponse: Objek response yang berisi data proyek.
        """

        return ProyekResponse(
            id=proyek.id,
            nama=proyek.nama,
            deskripsi=proyek.deskripsi,
            status=proyek.status,
            author_id=proyek.created_by_id,
            created_at=proyek.created_at,
            updated_at=proyek.updated_at,
        )
