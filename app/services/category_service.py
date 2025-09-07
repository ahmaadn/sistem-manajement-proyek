from app.db.models.category_model import Category
from app.db.models.project_member_model import RoleProject
from app.db.models.role_model import Role
from app.db.models.task_model import Task
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.schemas.user import User
from app.utils import exceptions


class CategoryService:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
        self.category_repo = uow.category_repo
        self.project_repo = uow.project_repo
        self.task_repo = uow.task_repo

    async def _ensure_is_owner(self, *, project_id: int, user_id: int):
        is_owner = await self.project_repo.ensure_member_in_project(
            project_id=project_id,
            user_id=user_id,
            required_role=RoleProject.OWNER,
        )

        if not is_owner:
            raise exceptions.ForbiddenError
        return is_owner

    async def _ensure_is_member(
        self,
        *,
        project_id: int,
        user_id: int,
        is_admin: bool,
        required_role: RoleProject | None = None,
    ):
        (
            is_project_exist,
            is_member,
        ) = await self.project_repo.get_project_membership_flags(
            project_id=project_id, user_id=user_id, required_role=required_role
        )

        if not is_project_exist:
            raise exceptions.ProjectNotFoundError

        if not is_admin and not is_member:
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk mengakses kategori pada proyek ini"
            )

    async def _ensure_category(self, category_id: int) -> Category:
        category = await self.category_repo.get_by_id(category_id=category_id)
        if not category:
            raise exceptions.CategoryNotFoundError("Kategori tidak ditemukan")
        return category

    async def _ensure_task(self, task_id: int) -> Task:
        task = await self.task_repo.get_by_id(task_id)
        if not task:
            raise exceptions.TaskNotFoundError
        return task

    async def create(
        self, *, project_id: int, payload: CategoryCreate, user: User
    ) -> Category:
        await self._ensure_is_member(
            project_id=project_id,
            user_id=user.id,
            is_admin=user.role == Role.ADMIN,
            required_role=RoleProject.OWNER,
        )

        return await self.category_repo.create(
            payload={"project_id": project_id, **payload.model_dump()}
        )

    async def list(self, *, project_id: int, user: User) -> list[Category]:
        await self._ensure_is_member(
            project_id=project_id,
            user_id=user.id,
            is_admin=user.role == Role.ADMIN,
        )

        return await self.category_repo.list_by_project(project_id=project_id)

    async def get(self, *, category_id: int, user: User) -> Category:
        category = await self.category_repo.get_by_id(category_id=category_id)
        if not category:
            raise exceptions.CategoryNotFoundError("Kategori tidak ditemukan")

        # Cek apakah user memiliki akses ke proyek kategori ini
        is_member = await self.project_repo.ensure_member_in_project(
            project_id=category.project_id, user_id=user.id
        )

        if user.role != Role.ADMIN and not is_member:
            raise exceptions.ForbiddenError(
                "Anda tidak memiliki izin untuk mengakses kategori pada proyek ini"
            )

        return category

    async def update(
        self, *, category_id: int, payload: CategoryUpdate, user: User
    ) -> Category:
        category = await self._ensure_category(category_id)

        # Cek apakah user memiliki akses ke proyek kategori ini
        await self._ensure_is_owner(project_id=category.project_id, user_id=user.id)

        return await self.category_repo.update(
            category=category, data=payload.model_dump(exclude_unset=True)
        )

    async def delete(self, *, category_id: int, user: User) -> None:
        category = await self._ensure_category(category_id)

        # Cek apakah user memiliki akses ke proyek kategori ini
        await self._ensure_is_owner(project_id=category.project_id, user_id=user.id)

        await self.category_repo.delete(category=category)

    async def assign(self, *, task_id: int, category_id: int, user: User) -> Task:
        task = await self._ensure_task(task_id)
        category = await self._ensure_category(category_id)

        if task.project_id != category.project_id:
            raise exceptions.InvalidCategoryAssignmentError(
                "Task dan kategori tidak berada dalam proyek yang sama"
            )

        # Cek apakah user memiliki akses ke proyek kategori ini
        await self._ensure_is_owner(project_id=task.project_id, user_id=user.id)

        return await self.category_repo.assign_to_task(task=task, category=category)

    async def unassign(self, *, task_id: int, user: User) -> Task:
        task = await self._ensure_task(task_id)

        # Cek apakah user memiliki akses ke proyek kategori ini
        await self._ensure_is_owner(project_id=task.project_id, user_id=user.id)

        return await self.category_repo.unassign_from_task(task=task)
