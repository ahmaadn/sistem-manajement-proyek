from dataclasses import dataclass

from app.core.domain.bus import DomainEvent  # gunakan base event Anda


@dataclass(frozen=True, kw_only=True)
class TaskCreatedEvent(DomainEvent):
    task_id: int
    project_id: int
    created_by: int


@dataclass(frozen=True, kw_only=True)
class TaskUpdatedEvent(DomainEvent):
    task_id: int
    project_id: int


@dataclass(frozen=True, kw_only=True)
class TaskDeletedEvent(DomainEvent):
    task_id: int
    project_id: int


@dataclass(frozen=True, kw_only=True)
class TaskAssignedEvent(DomainEvent):
    task_id: int
    project_id: int
    user_id: int


@dataclass(frozen=True, kw_only=True)
class TaskStatusChangedEvent(DomainEvent):
    task_id: int
    project_id: int
    new_status: str
    old_status: str


@dataclass(frozen=True, kw_only=True)
class SubTasksDetachedFromSectionEvent(DomainEvent):
    section_task_id: int
    project_id: int
    detached_count: int
