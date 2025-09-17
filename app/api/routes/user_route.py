from fastapi import APIRouter, Depends, Query, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import (
    get_current_user,
    get_user_admin,
    get_user_service,
    permission_required,
)
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.pagination import UserPaginationSchema
from app.schemas.user import User, UserDetail
from app.services.user_service import UserService
from app.utils.exceptions import AppErrorResponse

r = router = APIRouter(tags=["users"])


@cbv(router)
class _User:
    user_service: UserService = Depends(get_user_service)
    uow: UnitOfWork = Depends(get_uow)  # NEW

    @r.get(
        "/users/me",
        response_model=UserDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {"description": "OK", "model": UserDetail},
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def me(self, user: User = Depends(get_current_user)) -> UserDetail:
        """Mendapatkan detail informasi dari user saat ini

        **Akses**: Semua User
        """
        detail = await self.user_service.get_user_detail(user=user)
        await self.uow.commit()  # commit jika ada role baru dibuat
        return detail

    @r.get(
        "/users/{user_id}",
        response_model=UserDetail,
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {"description": "OK", "model": UserDetail},
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Tidak punyak akses",
                "model": AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
        dependencies=[
            Depends(permission_required([Role.ADMIN, Role.PROJECT_MANAGER]))
        ],
    )
    async def get_user_info(self, user_id: int) -> UserDetail:
        """Mendapatkan detail user. hanyaa bisa di akses oleh admin dan project
            manajer

        **Akses** : Admin, Project Manajer
        """
        user = await self.user_service.get_user(user_id=user_id)
        detail = await self.user_service.get_user_detail(user=user)
        await self.uow.commit()
        return detail

    @r.get(
        "/users",
        response_model=UserPaginationSchema[User],
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "OK",
                "model": UserPaginationSchema[User],
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Tidak punyak akses",
                "model": AppErrorResponse,
            },
        },
        dependencies=[
            Depends(permission_required([Role.ADMIN, Role.PROJECT_MANAGER]))
        ],
    )
    async def list_users(
        self,
        page: int = Query(1, ge=1, description="Halaman ke-X"),
        per_page: int = Query(
            100,
            ge=10,
            le=1000,
            description="Jumlah user per halaman (min 10, max 100)",
        ),
        search: str | None = Query(
            None, description="Kata kunci pencarian nama/email (opsional)"
        ),
    ) -> UserPaginationSchema[User]:
        """Mendapatkan semua user dengan pagination sederhana dan pencarian.

        **Akses**: Admin, Project Manajer
        """
        users, raw = await self.user_service.list_user(
            page=page, per_page=per_page, search=search
        )
        await self.uow.commit()

        def build_meta(r: dict, default_page: int, default_per_page: int):
            def _to_int(v):
                try:
                    return int(v)
                except Exception:
                    return None

            if not isinstance(r, dict):
                return {
                    "total_items": None,
                    "curr_page": default_page,
                    "per_page": default_per_page,
                    "next_page": None,
                    "prev_page": None,
                }
            total_items = (
                _to_int(r.get("total")) if r.get("total") is not None else None
            )
            per_page_val = _to_int(r.get("per_page")) or default_per_page
            curr_page_val = _to_int(r.get("current_page")) or default_page
            return {
                "total_items": total_items,
                "curr_page": curr_page_val,
                "per_page": per_page_val,
                "next_page": r.get("next_page_url"),
                "prev_page": r.get("prev_page_url"),
            }

        meta = build_meta(raw, page, per_page)
        total_page = 1
        if meta["total_items"] is not None and meta["per_page"]:
            total_page = (meta["total_items"] + meta["per_page"] - 1) // meta[
                "per_page"
            ]
        return UserPaginationSchema[User](
            count=len(users),
            items=users,
            curr_page=meta["curr_page"],
            total_page=total_page,
            next_page=meta["next_page"],
            previous_page=meta["prev_page"],
            per_page=meta["per_page"],
            total_items=meta["total_items"],
        )

    @r.patch(
        "/users/{user_id}/role",
        status_code=status.HTTP_200_OK,
        responses={
            status.HTTP_200_OK: {
                "description": "Peran pengguna berhasil diubah",
                "model": dict,
            },
            status.HTTP_401_UNAUTHORIZED: {
                "description": "Tidak punyak akses",
                "model": AppErrorResponse,
            },
            status.HTTP_404_NOT_FOUND: {
                "description": "Pengguna tidak ditemukan",
                "model": AppErrorResponse,
            },
        },
    )
    async def change_role(
        self, user_id: int, new_role: Role, admin: User = Depends(get_user_admin)
    ):
        """Mengubah peran pengguna

        **Akses**: Admin
        """
        await self.user_service.change_user_role(
            actor=admin, user_id=user_id, new_role=new_role
        )
        await self.uow.commit()
        return {"message": "Peran pengguna berhasil diubah"}
