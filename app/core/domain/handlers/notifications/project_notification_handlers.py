import asyncio
import logging

from fastapi.encoders import jsonable_encoder

from app.api.dependencies.sessions import async_session_maker
from app.core.domain.bus import subscribe_background
from app.core.domain.event import EventType
from app.core.domain.events.project import (
    ProjectCreatedEvent,
    ProjectStatusChangedEvent,
)
from app.core.domain.handlers.notification_wriite_handler import write_notifications
from app.core.realtime.notification import send_to_user
from app.schemas.notification import NotificationRead

logger = logging.getLogger(__name__)


async def notification_on_create_project(ev: ProjectCreatedEvent) -> None:
    """Hendel event pembuatan project

    Args:
        ev (ProjectCreatedEvent): event project created
    """

    async with async_session_maker() as session:
        message = f"Project '{ev.project_title}' has been created by {ev.user.name}."

        # mengirimkan notifikasi hanya kepada admin saja
        notifications = await write_notifications(
            recipients=ev.admin_recipients,
            actor_id=ev.user.id,
            message=message,
            notif_type=EventType.PROJECT_CREATED,
            project_id=ev.project_id,
            session=session,
        )

        asyncio.gather(
            *[
                send_to_user(
                    user_id=notif.recipient_id,
                    type_=notif.type,
                    data=jsonable_encoder(
                        NotificationRead(
                            id=notif.id,
                            recipient_id=notif.recipient_id,
                            type=notif.type,
                            message=message,
                            project_id=ev.project_id,
                            project_title=ev.project_title,
                            actor_id=ev.user.id,
                            actor_name=ev.user.name,
                            actor_profile_url=ev.user.profile_url,
                            created_at=notif.created_at,
                        )
                    ),
                )
                for notif in notifications
            ]
        )

        await session.commit()

    logger.debug("Notification for project created event handled.")


async def notification_on_project_change_status(ev: ProjectStatusChangedEvent):
    async with async_session_maker() as session:
        message = (
            f"Project '{ev.project_title}' status changed from {ev.before} to "
            f"{ev.after} by {ev.user.name}."
        )

        notifications = await write_notifications(
            recipients=list(ev.recipients),
            actor_id=ev.user.id,
            message=message,
            notif_type=EventType.PROJECT_STATUS_CHANGED,
            project_id=ev.project_id,
            session=session,
        )

        await asyncio.gather(
            *[
                send_to_user(
                    user_id=notif.recipient_id,
                    type_=notif.type,
                    data=jsonable_encoder(
                        NotificationRead(
                            id=notif.id,
                            recipient_id=notif.recipient_id,
                            type=notif.type,
                            message=message,
                            project_id=ev.project_id,
                            project_title=ev.project_title,
                            actor_id=ev.user.id,
                            actor_name=ev.user.name,
                            actor_profile_url=ev.user.profile_url,
                            created_at=notif.created_at,
                            task_id=notif.task_id,
                        )
                    ),
                )
                for notif in notifications
            ]
        )

        await session.commit()
    logger.debug("Notification for project status changed event handled.")


def register_event_handlers():
    subscribe_background(ProjectCreatedEvent, notification_on_create_project)
    subscribe_background(
        ProjectStatusChangedEvent, notification_on_project_change_status
    )
