from app.core.domain.bus import subscribe
from app.core.domain.events.task import (
    SubTasksDetachedFromSectionEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskRenameEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)
from app.core.domain.handlers.audit_handlers import write_audit
from app.db.models.audit_model import AuditEventType


async def on_task_created(ev: TaskCreatedEvent):
    """Audit event untuk tugas yang dibuat."""

    await write_audit(
        action_type=AuditEventType.TASK_CREATED,
        performed_by=ev.created_by,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={"item_type": ev.item_type, "task_name": ev.task_name},
    )

    print("[INFO] Task created:", ev.task_name)


async def on_task_renamed(ev: TaskRenameEvent):
    """Audit event untuk tugas yang diubah namanya."""

    await write_audit(
        action_type=AuditEventType.TASK_TITLE_CHANGED,
        performed_by=ev.updated_by,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={"before": ev.before, "after": ev.after},
    )


async def on_task_updated(event: TaskUpdatedEvent):
    """Audit event untuk tugas yang diubah namanya."""

    await write_audit(
        action_type=AuditEventType.TASK_UPDATED,
        performed_by=event.updated_by,
        task_id=event.task_id,
        project_id=event.project_id,
    )


async def on_task_deleted(event: TaskDeletedEvent):
    """Audit event untuk tugas yang dihapus."""

    await write_audit(
        action_type=AuditEventType.TASK_DELETED,
        performed_by=event.deleted_by,
        task_id=event.task_id,
        project_id=event.project_id,
    )


async def on_task_status_changed(event: TaskStatusChangedEvent):
    """Audit event untuk tugas yang diubah statusnya."""

    await write_audit(
        action_type=AuditEventType.TASK_STATUS_CHANGED,
        performed_by=event.user_id,
        task_id=event.task_id,
        project_id=event.project_id,
        details={"new_status": event.new_status, "old_status": event.old_status},
    )


async def on_task_detached(event: SubTasksDetachedFromSectionEvent):
    """Audit event untuk sub-tugas yang dipisahkan dari seksi."""

    await write_audit(
        action_type=AuditEventType.SUBTASKS_DETACHED,
        performed_by=event.user_id,
        task_id=event.section_task_id,
        project_id=event.project_id,
        details={"detached_count": event.detached_count},
    )


def register_event_handlers():
    subscribe(TaskCreatedEvent, on_task_created)
    subscribe(TaskRenameEvent, on_task_renamed)
    subscribe(TaskUpdatedEvent, on_task_updated)
    subscribe(TaskDeletedEvent, on_task_deleted)
    subscribe(TaskStatusChangedEvent, on_task_status_changed)
    subscribe(SubTasksDetachedFromSectionEvent, on_task_detached)
