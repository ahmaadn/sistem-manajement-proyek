from typing import Literal, cast

from pydantic import computed_field

from app.core.domain.event import EventType
from app.schemas.base import BaseSchema

# -----------------------------------------------------------------
# Schemas for Task Audit Events
# -----------------------------------------------------------------


class TaskStatusChangeAuditSchema(BaseSchema):
    old_status: str
    new_status: str


class TaskTitleChangeAuditSchema(BaseSchema):
    before: str
    after: str


class TaskAssignAddedAuditSchama(BaseSchema):
    assignee_id: str
    assignee_name: str


class TaskAssignRemovedAuditSchama(BaseSchema):
    assignee_id: str
    assignee_name: str


type TaskAuditListSchema = (
    TaskAuditSchema
    | TaskStatusChangeAuditSchema
    | TaskTitleChangeAuditSchema
    | TaskAssignAddedAuditSchama
    | TaskAssignRemovedAuditSchama
)

type TaskActionType = Literal[
    EventType.TASK_STATUS_CHANGED,
    EventType.TASK_TITLE_CHANGED,
    EventType.TASK_ASSIGNED_ADDED,
    EventType.TASK_ASSIGNED_REMOVED,
]


class TaskAuditSchema(BaseSchema):
    audit_id: int
    user_id: int
    profile_url: int
    user_name: str
    task_id: str
    created_at: str
    action_type: TaskActionType
    details: TaskAuditListSchema

    @computed_field(return_type=str)
    def content(self) -> str:
        """Konten deskriptif otomatis untuk setiap event audit.

        Dikalkulasi dari ``action_type`` dan ``details`` dan akan otomatis
        ikut saat ``model_dump()`` dipanggil.
        """
        try:
            if self.action_type == EventType.TASK_STATUS_CHANGED:
                det = cast(TaskStatusChangeAuditSchema, self.details)
                return (
                    f"Status changed from '{det.old_status}' to '{det.new_status}'"
                )
            if self.action_type == EventType.TASK_TITLE_CHANGED:
                det = cast(TaskTitleChangeAuditSchema, self.details)
                return f"Title changed from '{det.before}' to '{det.after}'"
            if self.action_type == EventType.TASK_ASSIGNED_ADDED:
                det = cast(TaskAssignAddedAuditSchama, self.details)
                name = det.assignee_name or det.assignee_id
                return f"Assignee added '{name}'"
            if self.action_type == EventType.TASK_ASSIGNED_REMOVED:
                det = cast(TaskAssignRemovedAuditSchama, self.details)
                name = det.assignee_name or det.assignee_id
                return f"Assignee removed '{name}'"
        except Exception:
            # Jika detail tidak sesuai ekspektasi, kembalikan string kosong.
            pass
        return ""
