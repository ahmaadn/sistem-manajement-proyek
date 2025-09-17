import asyncio

from fastapi.encoders import jsonable_encoder

from app.api.dependencies.sessions import async_session_maker
from app.core.domain.bus import subscribe_background
from app.core.domain.event import EventType
from app.core.domain.events.project_member import ProjectMemberAddedEvent
from app.core.domain.handlers.notification_wriite_handler import write_notifications
from app.core.realtime.notification import send_to_user
from app.schemas.notification import NotificationRead


async def notification_on_member_added(ev: ProjectMemberAddedEvent):
    async with async_session_maker() as session:
        message = (
            f"You have been added to the project '{ev.project_title}' with "
            f"the role of {ev.new_role} by {ev.user.name}."
        )

        notifications = await write_notifications(
            recipients=[ev.member_id],
            actor_id=ev.performed_by,  # type: ignore
            message=message,
            notif_type=EventType.PROJECT_MEMBER_ADDED,
            project_id=ev.project_id,
            session=session,
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


def register_event_handlers():
    subscribe_background(ProjectMemberAddedEvent, notification_on_member_added)
