import asyncio

from fastapi.encoders import jsonable_encoder

from app.core.domain.bus import subscribe_background
from app.core.domain.event import EventType
from app.core.domain.events.assignee_task import TaskAssignedAddedEvent
from app.core.domain.handlers.notification_wriite_handler import write_notifications
from app.core.realtime.notification import send_to_user
from app.db.base import async_session_maker
from app.schemas.notification import NotificationRead


async def notification_user_assigned_to_task(ev: TaskAssignedAddedEvent):
    async with async_session_maker() as session:
        message = (
            f"You have been assigned to the task '{ev.task_name}' in "
            "project '{ev.project_title}'."
        )

        notifications = await write_notifications(
            recipients=[ev.assignee_id],
            actor_id=ev.performed_by,  # type: ignore
            message=message,
            notif_type=EventType.TASK_ASSIGNED_ADDED,
            project_id=ev.project_id,
            task_id=ev.task_id,
            session=session,
            send_to_me=False,
        )

        asyncio.gather(
            *[
                send_to_user(
                    user_id=notif.recipient_id,
                    type_=EventType.NOTIFICATION_SENT,
                    data=jsonable_encoder(
                        NotificationRead(
                            id=notif.id,
                            recipient_id=notif.recipient_id,
                            type=notif.type,
                            message=message,
                            project_id=ev.project_id,
                            project_title=ev.project_title,
                            actor_id=ev.performed_by,  # type: ignore
                            actor_name=ev.performed_name,
                            actor_profile_url=ev.performed_profile_url,
                            created_at=notif.created_at,
                        )
                    ),
                )
                for notif in notifications
            ]
        )


def register_event_handlers():
    subscribe_background(TaskAssignedAddedEvent, notification_user_assigned_to_task)
