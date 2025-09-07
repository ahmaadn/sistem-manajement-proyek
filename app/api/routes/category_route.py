from fastapi import APIRouter, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_category_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user, permission_required
from app.db.models.role_model import Role
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.category import CategoryCreate, CategoryRead, CategoryUpdate
from app.schemas.user import User
from app.services.category_service import CategoryService

router = APIRouter(tags=["Category"])


@cbv(router)
class _Category:
    user: User = Depends(get_current_user)
    uow: UnitOfWork = Depends(get_uow)
    category_service: CategoryService = Depends(get_category_service)

    @router.post(
        "/projects/{project_id}/categories",
        response_model=CategoryRead,
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def create_category(self, project_id: int, payload: CategoryCreate):
        """Membuat kategori baru pada proyek.

        **Akses**: pemilik proyek (Owner)
        """
        async with self.uow:
            cat = await self.category_service.create(
                project_id=project_id, payload=payload, user=self.user
            )
            await self.uow.commit()
        return cat

    @router.get(
        "/projects/{project_id}/categories",
        response_model=list[CategoryRead],
        status_code=status.HTTP_200_OK,
    )
    async def list_categories(self, project_id: int):
        """List kategori berdasarkan ID proyek.

        **Akses**: Admin, member proyek (Owner, Member, Viewer)
        """
        return await self.category_service.list(
            project_id=project_id, user=self.user
        )

    @router.get(
        "/categories/{category_id}",
        response_model=CategoryRead,
        status_code=status.HTTP_200_OK,
    )
    async def get_category(self, category_id: int):
        """
        Mendapatkan detail kategori berdasarkan ID.

        **Akses**: Admin, member proyek (Owner, Member)
        """
        return await self.category_service.get(
            category_id=category_id, user=self.user
        )

    @router.put(
        "/categories/{category_id}",
        response_model=CategoryRead,
        status_code=status.HTTP_200_OK,
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def update_category(self, category_id: int, payload: CategoryUpdate):
        """Update kategori berdasarkan ID.

        **Akses**: pemilik proyek (Owner)
        """
        async with self.uow:
            cat = await self.category_service.update(
                category_id=category_id, payload=payload, user=self.user
            )
            await self.uow.commit()
        return cat

    @router.delete(
        "/categories/{category_id}",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def delete_category(self, project_id: int, category_id: int) -> None:
        """
        Menghapus kategori berdasarkan ID.

        **Akses**: pemilik proyek (Owner)
        """
        async with self.uow:
            await self.category_service.delete(
                category_id=category_id, user=self.user
            )
            await self.uow.commit()

    @router.post(
        "/tasks/{task_id}/categories/{category_id}/assign",
        status_code=status.HTTP_201_CREATED,
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def assign_category(self, task_id: int, category_id: int) -> None:
        """Menugaskan kategori ke tugas.

        **Akses**: pemilik proyek (Owner)
        """
        async with self.uow:
            await self.category_service.assign(
                task_id=task_id, category_id=category_id, user=self.user
            )
            await self.uow.commit()

    @router.delete(
        "/tasks/{task_id}/categories/unassign",
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[
            Depends(permission_required([Role.PROJECT_MANAGER, Role.ADMIN]))
        ],
    )
    async def unassign_category(self, task_id: int):
        """Menghapus penugasan kategori dari tugas.

        **Akses**: pemilik proyek (Owner)
        """
        async with self.uow:
            await self.category_service.unassign(task_id=task_id, user=self.user)
            await self.uow.commit()
