from types import NoneType

from fastapi import APIRouter, Body, Depends, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_task_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user, get_user_service
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.user import User
from app.services.task_service import TaskService
from app.services.user_service import UserService

r = router = APIRouter(tags=["Assignee Task"])


@cbv(r)
class _Task:
    user: User = Depends(get_current_user)
    task_service: TaskService = Depends(get_task_service)
    user_service: UserService = Depends(get_user_service)
    uow: UnitOfWork = Depends(get_uow)

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

        target_user = await user_service.get_user(user_id)

        async with self.uow:
            await self.task_service.assign_user(
                actor=self.user, task_id=task_id, target_user=target_user
            )
            await self.uow.commit()

    @r.delete("/tasks/{task_id}/unassign", status_code=status.HTTP_202_ACCEPTED)
    async def unassign_task(self, task_id: int, user_id: int):
        """
        Menghapus penugasan pengguna dari tugas tertentu.

        **Akses** : Project Manager (Owner), Admin
        """

        target_user = await self.user_service.get_user(user_id)

        async with self.uow:
            await self.task_service.unassign_user(
                actor=self.user, target_user=target_user, task_id=task_id
            )
            await self.uow.commit()
