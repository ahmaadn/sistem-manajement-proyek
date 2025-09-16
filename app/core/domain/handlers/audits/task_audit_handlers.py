import logging

from fastapi.encoders import jsonable_encoder

from app.core.domain.bus import subscribe
from app.core.domain.event import EventType
from app.core.domain.events.task import (
    SubTasksDetachedFromSectionEvent,
    TaskCreatedEvent,
    TaskDeletedEvent,
    TaskRenameEvent,
    TaskStatusChangedEvent,
    TaskUpdatedEvent,
)
from app.core.domain.handlers.audit_handler import write_audit

logger = logging.getLogger(__name__)


async def on_task_created(ev: TaskCreatedEvent):
    """Audit event untuk tugas yang dibuat."""

    await write_audit(
        action_type=EventType.TASK_CREATED,
        performed_by=ev.created_by,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={"item_type": ev.item_type, "task_name": ev.task_name},
    )

    logger.info(f"Task created: {ev.task_name}")


async def on_task_renamed(ev: TaskRenameEvent):
    """Audit event untuk tugas yang diubah namanya."""

    await write_audit(
        action_type=EventType.TASK_TITLE_CHANGED,
        performed_by=ev.updated_by,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={"before": ev.before, "after": ev.after},
    )
    logger.info(f"Task renamed: {ev.before} to {ev.after}")


async def on_task_updated(ev: TaskUpdatedEvent):
    """Audit event untuk tugas yang diubah namanya."""

    await write_audit(
        action_type=EventType.TASK_UPDATED,
        performed_by=ev.updated_by,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details=jsonable_encoder(ev.details),
    )
    logger.info(f"Task updated: {ev.task_id}")


async def on_task_deleted(ev: TaskDeletedEvent):
    """Audit event untuk tugas yang dihapus."""

    await write_audit(
        action_type=EventType.TASK_DELETED,
        performed_by=ev.deleted_by,
        task_id=None,
        project_id=ev.project_id,
    )

    logger.info(f"Task deleted: {ev.task_name}")


async def on_task_status_changed(ev: TaskStatusChangedEvent):
    """Audit event untuk tugas yang diubah statusnya."""

    await write_audit(
        action_type=EventType.TASK_STATUS_CHANGED,
        performed_by=ev.performed_by,
        task_id=ev.task_id,
        project_id=ev.project_id,
        details={"new_status": ev.new_status, "old_status": ev.old_status},
    )

    logger.info(
        f"Task status changed: {ev.task_id} from {ev.old_status} to {ev.new_status}"
    )


async def on_task_detached(ev: SubTasksDetachedFromSectionEvent):
    """Audit event untuk sub-tugas yang dipisahkan dari seksi."""

    await write_audit(
        action_type=EventType.SUBTASKS_DETACHED,
        performed_by=ev.user_id,
        task_id=ev.section_task_id,
        project_id=ev.project_id,
        details={"detached_count": ev.detached_count},
    )
    logger.info(
        f"Sub-tasks detached from section task: {ev.section_task_id}, "
        f"detached count: {ev.detached_count}"
    )


def register_event_handlers():
    subscribe(TaskCreatedEvent, on_task_created)
    subscribe(TaskRenameEvent, on_task_renamed)
    subscribe(TaskUpdatedEvent, on_task_updated)
    subscribe(TaskDeletedEvent, on_task_deleted)
    subscribe(TaskStatusChangedEvent, on_task_status_changed)
    subscribe(SubTasksDetachedFromSectionEvent, on_task_detached)
