import logging

from app.core.domain.bus import subscribe
from app.core.domain.events.project_member import (
    ProjectMemberAddedEvent,
    ProjectMemberRemovedEvent,
    ProjectMemberUpdatedEvent,
)
from app.core.domain.handlers.audit_handler import write_audit
from app.db.models.audit_model import AuditEventType

logger = logging.getLogger(__name__)


async def on_project_member_added(ev: ProjectMemberAddedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_MEMBER_ADDED,
        performed_by=ev.performed_by,
        project_id=ev.project_id,
        details={
            "member_id": ev.member_id,
            "member_name": ev.member_name,
            "new_role": ev.new_role,
        },
    )
    logger.info(
        f"Audit log created for project member addition: {ev.member_name!r} ",
        f"to project ID {ev.project_id}",
    )


async def on_project_member_updated(ev: ProjectMemberUpdatedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_MEMBER_UPDATED,
        performed_by=ev.performed_by,
        project_id=ev.project_id,
        details={
            "member_id": ev.member_id,
            "member_name": ev.member_name,
            "before": ev.before,
            "after": ev.after,
        },
    )
    logger.info(
        f"Audit log created for project member update: {ev.member_name!r} ",
        f"to project ID {ev.project_id}",
    )


async def on_project_member_removed(ev: ProjectMemberRemovedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_MEMBER_REMOVED,
        performed_by=ev.performed_by,
        project_id=ev.project_id,
        details={
            "member_id": ev.member_id,
            "member_name": ev.member_name,
        },
    )
    logger.info(
        f"Audit log created for project member removal: {ev.member_name!r} ",
        f"from project ID {ev.project_id}",
    )


def register_event_handlers():
    subscribe(ProjectMemberAddedEvent, on_project_member_added)
    subscribe(ProjectMemberUpdatedEvent, on_project_member_updated)
    subscribe(ProjectMemberRemovedEvent, on_project_member_removed)
