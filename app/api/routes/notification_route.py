from fastapi import APIRouter, Depends, Query, status
from fastapi_utils.cbv import cbv

from app.api.dependencies.services import get_notification_service
from app.api.dependencies.uow import get_uow
from app.api.dependencies.user import get_current_user
from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.notification import NotificationRead
from app.schemas.user import User
from app.services.notification_service import NotificationService

r = router = APIRouter(tags=["Notification"])


@cbv(r)
class _Notification:
    user: User = Depends(get_current_user)
    service: NotificationService = Depends(get_notification_service)
    uow: UnitOfWork = Depends(get_uow)

    @r.get(
        "/users/me/notification",
        response_model=list[NotificationRead],
        status_code=status.HTTP_200_OK,
    )
    async def get_all_notification(
        self,
        read: bool | None = Query(
            None, description="Filter status baca: true=terbaca, false=belum"
        ),
        sort: str = Query(
            "terbaru", regex="^(terbaru|terlama)$", description="Urutan sort"
        ),
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ):
        return await self.service.list_notifications(
            user_id=self.user.id,
            only_read=read,
            sort=sort,  # type: ignore[arg-type]
            limit=limit,
            offset=offset,
        )

    @r.patch(
        "/notification/{notif_id}/read",
        response_model=NotificationRead,
        status_code=status.HTTP_200_OK,
    )
    async def read_notification(self, notif_id: int):
        async with self.uow:
            item = await self.service.read_notification(
                notif_id=notif_id, user_id=self.user.id
            )
            await self.uow.commit()
        return item
