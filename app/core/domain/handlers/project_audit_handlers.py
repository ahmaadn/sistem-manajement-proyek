from app.core.domain.bus import subscribe
from app.core.domain.events.project import (
    ProjectCreatedEvent,
    ProjectStatusChangedEvent,
    ProjectUpdatedEvent,
)
from app.core.domain.handlers.audit_handlers import write_audit
from app.db.models.audit_model import AuditEventType


async def on_create_project(ev: ProjectCreatedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_CREATED,
        performed_by=ev.user_id,
        project_id=ev.project_id,
        details={"project_title": ev.project_title},
    )
    print(f"[INFO] Audit log created for project creation: {ev.project_title}")


async def on_update_project(ev: ProjectUpdatedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_UPDATED,
        performed_by=ev.user_id,
        project_id=ev.project_id,
        details={"project_title": ev.project_title},
    )
    print(f"[INFO] Audit log created for project update: {ev.project_title}")


async def on_status_change_project(ev: ProjectStatusChangedEvent):
    await write_audit(
        action_type=AuditEventType.PROJECT_STATUS_CHANGED,
        performed_by=ev.user_id,
        project_id=ev.project_id,
        details={"before": ev.before, "after": ev.after},
    )
    print(f"[INFO] Audit log created for project status change: {ev.project_id}")


def register_event_handlers():
    subscribe(ProjectCreatedEvent, on_create_project)
    subscribe(ProjectUpdatedEvent, on_update_project)
    subscribe(ProjectStatusChangedEvent, on_status_change_project)
