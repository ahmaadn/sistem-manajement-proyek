import logging

from app.core.domain.bus import subscribe
from app.core.domain.events.user import UserRoleAssignedEvent
from app.core.domain.handlers.audit_handler import write_audit
from app.db.models.audit_model import AuditEventType

logger = logging.getLogger(__name__)


async def on_assignee_role_to_user(ev: UserRoleAssignedEvent):
    await write_audit(
        action_type=AuditEventType.USER_ROLE_ASSIGNED,
        details={
            "assignee_id": ev.assignee_id,
            "assignee_name": ev.assignee_name,
            "assignee_role": ev.assignee_role,
        },
    )
    logger.info(f"User role assigned: {ev.assignee_name} as {ev.assignee_role}")


def register_event_handlers():
    subscribe(UserRoleAssignedEvent, on_assignee_role_to_user)
