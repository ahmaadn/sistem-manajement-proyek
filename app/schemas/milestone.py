from datetime import datetime
from typing import List, Optional

from pydantic import Field

from app.db.models.task_model import PriorityLevel, StatusTask
from app.schemas.base import BaseSchema
from app.schemas.task import TaskAssigneeRead


class MilestoneBase(BaseSchema):
    title: str = Field(..., max_length=255)


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneRead(MilestoneBase):
    id: int
    project_id: int
    title: str
    display_order: int
    created_at: datetime
    updated_at: datetime | None = None


class MilestoneUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=255)


class MilestoneTaskBase(BaseSchema):
    id: int
    name: str = Field(default="Untitled Task")
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int | None = Field(default=None)
    due_date: datetime | None = Field(default=None)
    start_date: datetime | None = Field(default=None)

    assignees: List[TaskAssigneeRead] = Field(
        default_factory=list,
        description="Daftar pengguna yang ditugaskan pada tugas ini.",
    )


class MilestoneSubTaskRead(MilestoneTaskBase):
    """Response schema untuk subtask dalam milestone."""


class MilestoneTaskRead(MilestoneTaskBase):
    """Response schema untuk subtask dalam milestone."""

    sub_tasks: List[MilestoneSubTaskRead] = Field(
        default_factory=list,
        description="Daftar subtask dari tugas ini.",
    )


class MilestoneDetail(BaseSchema):
    id: int
    project_id: int
    title: str
    display_order: int
    created_at: datetime
    updated_at: datetime | None = None
    tasks: list[MilestoneTaskRead]
