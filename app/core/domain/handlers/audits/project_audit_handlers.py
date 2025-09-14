import logging

from app.core.domain.bus import subscribe
from app.core.domain.event import EventType
from app.core.domain.events.project import (
    ProjectCreatedEvent,
    ProjectStatusChangedEvent,
    ProjectUpdatedEvent,
)
from app.core.domain.handlers.audit_handler import write_audit

logger = logging.getLogger(__name__)


async def on_create_project(ev: ProjectCreatedEvent):
    logger.info("Audit log created for project creation: %s", ev.project_title)
    await write_audit(
        action_type=EventType.PROJECT_CREATED,
        performed_by=ev.performed_by,
        project_id=ev.project_id,
        details={"project_title": ev.project_title},
    )


async def on_update_project(ev: ProjectUpdatedEvent):
    await write_audit(
        action_type=EventType.PROJECT_UPDATED,
        performed_by=ev.performed_by,
        project_id=ev.project_id,
        details={"project_title": ev.project_title},
    )
    logger.info("Audit log created for project update: %s", ev.project_title)


async def on_status_change_project(ev: ProjectStatusChangedEvent):
    logger.info(f"Audit log created for project status change: {ev.project_id}")
    await write_audit(
        action_type=EventType.PROJECT_STATUS_CHANGED,
        performed_by=ev.performed_by,
        project_id=ev.project_id,
        details={"before": ev.before, "after": ev.after},
    )


def register_event_handlers():
    subscribe(ProjectCreatedEvent, on_create_project)
    subscribe(ProjectUpdatedEvent, on_update_project)
    subscribe(ProjectStatusChangedEvent, on_status_change_project)
