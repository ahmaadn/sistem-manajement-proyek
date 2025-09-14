from __future__ import annotations

from typing import Literal

from app.db.uow.sqlalchemy import UnitOfWork
from app.schemas.notification import NotificationRead
from app.services.pegawai_service import PegawaiService
from app.utils import exceptions


class NotificationService:
    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def list_notifications(
        self,
        *,
        user_id: int,
        only_read: bool | None = None,
        sort: Literal["terbaru", "terlama"] = "terbaru",
        limit: int = 100,
        offset: int = 0,
    ) -> list[NotificationRead]:
        order = "desc" if sort == "terbaru" else "asc"
        notifs = await self.uow.notification_repo.list_by_recipient(
            recipient_id=user_id,
            only_read=only_read,
            order=order,
            limit=limit,
            offset=offset,
        )

        actor_ids = list({n.actor_id for n in notifs})
        pegawai = PegawaiService()
        actors = await pegawai.list_user_by_ids(actor_ids)

        def actor_info(user_id: int):
            for u in actors:
                if u and u.id == user_id:
                    return u.name or "", getattr(u, "profile_url", None)
            return "", None

        items: list[NotificationRead] = []
        for n in notifs:
            a_name, a_profile = actor_info(n.actor_id)
            items.append(
                NotificationRead(
                    id=n.id,
                    recipient_id=n.recipient_id,
                    type=n.type,
                    message=n.message,
                    created_at=n.created_at,
                    actor_id=n.actor_id,
                    actor_name=a_name,
                    actor_profile_url=a_profile,
                    project_id=n.project_id or 0,
                    project_title=getattr(n.project, "title", None),
                    task_id=n.task_id,
                    task_name=getattr(n.task, "name", None),
                    is_read=n.is_read,
                    read_at=n.read_at,
                )
            )
        return items

    async def read_notification(
        self, *, notif_id: int, user_id: int
    ) -> NotificationRead:
        notif = await self.uow.notification_repo.get_for_user(
            notif_id=notif_id, user_id=user_id
        )
        if not notif:
            # Either not found or not belonging to the user
            raise exceptions.ForbiddenError(
                "Notifikasi tidak ditemukan atau tidak milik Anda"
            )

        notif = await self.uow.notification_repo.mark_read(notif=notif)

        # enrich actor info
        pegawai = PegawaiService()
        actor = (await pegawai.list_user_by_ids([notif.actor_id]))[0]
        actor_name = actor.name if actor else ""
        actor_profile = getattr(actor, "profile_url", None) if actor else None

        return NotificationRead(
            id=notif.id,
            recipient_id=notif.recipient_id,
            type=notif.type,
            message=notif.message,
            created_at=notif.created_at,
            actor_id=notif.actor_id,
            actor_name=actor_name,
            actor_profile_url=actor_profile,
            project_id=notif.project_id or 0,
            project_title=getattr(notif.project, "title", None),
            task_id=notif.task_id,
            task_name=getattr(notif.task, "name", None),
            is_read=notif.is_read,
            read_at=notif.read_at,
        )
