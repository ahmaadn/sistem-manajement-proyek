from types import NoneType

from fastapi import APIRouter, Body, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_project_service, get_task_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user, get_user_service
from app.db.models.project_member_model import ProjectMember, RoleProject
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.user import User
from app.services.project_service import ProjectService
from app.services.task_service import TaskService
from app.services.user_service import UserService
from app.utils import exceptions

r = router = APIRouter(tags=["Assignee Task"])


@cbv(r)
class _Task:
    user: User = Depends(get_current_user)
    task_service: TaskService = Depends(get_task_service)
    project_service: ProjectService = Depends(get_project_service)
    user_service: UserService = Depends(get_user_service)
    uow: UnitOfWork = Depends(get_uow)

    # Helper: pastikan user adalah member project
    async def _ensure_project_member(self, project_id: int) -> ProjectMember:
        try:
            return await self.project_service.get_member(project_id, self.user.id)
        except exceptions.MemberNotFoundError:
            raise exceptions.UserNotInProjectError from None

    async def _ensure_project_owner(self, project_id: int) -> ProjectMember:
        project_member = await self._ensure_project_member(project_id)
        if project_member.role != RoleProject.OWNER:
            raise exceptions.ForbiddenError
        return project_member

    @r.post("/tasks/{task_id}/assign", status_code=status.HTTP_201_CREATED)
    async def assign_task(
        self,
        task_id: int,
        user_id: int = Body(..., embed=True),
        user_service: UserService = Depends(get_user_service),
    ) -> NoneType:
        """
        Menugaskan pengguna untuk tugas tertentu.

        **Akses** : Project Manager (Owner)
        """

        user = await user_service.get_user(user_id)

        task = await self.task_service.get(task_id)
        if task is None:
            raise exceptions.TaskNotFoundError

        await self._ensure_project_owner(task.project_id)

        async with self.uow:
            await self.task_service.assign_user(self.user.id, task_id, user=user)
            await self.uow.commit()

    @r.delete("/tasks/{task_id}/unassign", status_code=status.HTTP_202_ACCEPTED)
    async def unassign_task(self, task_id: int, user_id: int):
        """
        Menghapus penugasan pengguna dari tugas tertentu.

        **Akses** : Project Manager (Owner)
        """

        user = await self.user_service.get_user(user_id)
        if not user:
            raise exceptions.UserNotFoundError("User not found")

        task = await self.task_service.get(task_id)
        if task is None:
            raise exceptions.TaskNotFoundError

        await self._ensure_project_owner(task.project_id)

        async with self.uow:
            await self.task_service.unassign_user(self.user.id, user, task)
            await self.uow.commit()
