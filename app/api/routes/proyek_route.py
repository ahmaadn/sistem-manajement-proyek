import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_utils.cbv import cbv
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.sessions import get_async_session
from app.db.models.proyek_model import Proyek
from app.schemas.proyek import ProyekCreate, ProyekResponse, ProyekUpdate
from app.utils.common import ErrorCode
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["Proyek"])


@cbv(r)
class _Proyek:
    session: AsyncSession = Depends(get_async_session)

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
        """buat proyek baru"""

        proyek_item = Proyek(
            nama=proyek.nama,
            deskripsi=proyek.deskripsi,
            status=proyek.status,
            created_by_id=1,  # Ganti dengan ID pengguna yang sesuai
        )

        self.session.add(proyek_item)
        await self.session.commit()
        await self.session.refresh(proyek_item)

        return ProyekResponse(
            id=proyek_item.id,
            nama=proyek_item.nama,
            deskripsi=proyek_item.deskripsi,
            status=proyek_item.status,
            author_id=proyek_item.created_by_id,
            created_at=proyek_item.created_at,
            updated_at=proyek_item.updated_at,
        )

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

        proyek_item = await self.session.get(Proyek, proyek_id)
        if not proyek_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": ErrorCode.PROYEK_NOT_FOUND,
                    "message": "Proyek tidak ditemukan",
                },
            )

        # Cek apakah sudah di delete
        if proyek_item.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": ErrorCode.PROYEK_NOT_FOUND,
                    "message": "Proyek tidak ditemukan",
                },
            )

        for key, value in proyek.dict(exclude_unset=True).items():
            setattr(proyek_item, key, value)

        self.session.add(proyek_item)
        await self.session.commit()
        await self.session.refresh(proyek_item)

        return ProyekResponse(
            id=proyek_item.id,
            nama=proyek_item.nama,
            deskripsi=proyek_item.deskripsi,
            status=proyek_item.status,
            author_id=proyek_item.created_by_id,
            created_at=proyek_item.created_at,
            updated_at=proyek_item.updated_at,
        )

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

        proyek_item = await self.session.get(Proyek, proyek_id)
        if not proyek_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error_code": ErrorCode.PROYEK_NOT_FOUND,
                    "message": "Proyek tidak ditemukan",
                },
            )

        proyek_item.deleted_at = datetime.datetime.now(datetime.timezone.utc)

        self.session.add(proyek_item)
        await self.session.commit()
        await self.session.refresh(proyek_item)
