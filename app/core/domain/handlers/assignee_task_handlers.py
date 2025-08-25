from app.core.domain.bus import subscribe
from app.core.domain.events.assignee_task import (
    TaskAssignedAddedEvent,
    TaskAssignedRemovedEvent,
)
from app.core.domain.handlers.audit_handlers import write_audit
from app.db.models.audit_model import AuditEventType


async def on_assignee_task_added(ev: TaskAssignedAddedEvent):
    await write_audit(
        action_type=AuditEventType.TASK_ASSIGNED_ADDED,
        performed_by=ev.user_id,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={
            "assignee_id": ev.assignee_id,
            "assignee_name": ev.assignee_name,
        },
    )


async def on_assignee_task_removed(ev: TaskAssignedRemovedEvent):
    await write_audit(
        action_type=AuditEventType.TASK_ASSIGNED_REMOVED,
        performed_by=ev.user_id,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={
            "assignee_id": ev.assignee_id,
            "assignee_name": ev.assignee_name,
        },
    )


def register_event_handlers():
    subscribe(TaskAssignedAddedEvent, on_assignee_task_added)
    subscribe(TaskAssignedRemovedEvent, on_assignee_task_removed)
