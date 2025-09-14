import datetime
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_on: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    performed_by: int | None = None

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def dump_model(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def json(self) -> str:
        return str(self.dump_model())


class EventType(StrEnum):
    # Task
    TASK_CREATED = "task_created"
    TASK_UPDATED = "task_updated"
    TASK_DELETED = "task_deleted"
    TASK_STATUS_CHANGED = "task_status_changed"
    TASK_DUE_DATE_CHANGED = "task_due_date_changed"
    TASK_PRIORITY_CHANGED = "task_priority_changed"
    TASK_TITLE_CHANGED = "task_title_changed"

    # Assign
    TASK_ASSIGNEE_ADDED = "task_assignee_added"
    TASK_ASSIGNEE_REMOVED = "task_assignee_removed"
    USER_ROLE_ASSIGNED = "user_role_assigned"

    # Project
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_REMOVED = "project_removed"
    PROJECT_MEMBER_ADDED = "project_member_added"
    PROJECT_MEMBER_UPDATED = "project_member_updated"
    PROJECT_MEMBER_REMOVED = "project_member_removed"
    PROJECT_STATUS_CHANGED = "project_status_changed"

    # subtask
    SUBTASKS_DETACHED = "subtasks_detached"

    # Assignment
    TASK_ASSIGNED_ADDED = "task_assigned_added"
    TASK_ASSIGNED_REMOVED = "task_assigned_removed"
