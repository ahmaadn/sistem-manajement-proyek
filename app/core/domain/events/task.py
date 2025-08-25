from dataclasses import dataclass

from app.core.domain.bus import DomainEvent  # gunakan base event Anda


@dataclass(frozen=True, kw_only=True)
class TaskCreatedEvent(DomainEvent):
    task_id: int
    project_id: int
    created_by: int
    item_type: str
    task_name: str


@dataclass(frozen=True, kw_only=True)
class TaskRenameEvent(DomainEvent):
    task_id: int
    project_id: int
    updated_by: int
    before: str
    after: str


@dataclass(frozen=True, kw_only=True)
class TaskUpdatedEvent(DomainEvent):
    task_id: int
    project_id: int
    updated_by: int


@dataclass(frozen=True, kw_only=True)
class TaskDeletedEvent(DomainEvent):
    task_id: int
    project_id: int
    deleted_by: int


@dataclass(frozen=True, kw_only=True)
class TaskStatusChangedEvent(DomainEvent):
    user_id: int
    task_id: int
    project_id: int
    new_status: str
    old_status: str


@dataclass(frozen=True, kw_only=True)
class SubTasksDetachedFromSectionEvent(DomainEvent):
    user_id: int
    section_task_id: int
    project_id: int
    detached_count: int
