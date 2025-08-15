import datetime

from pydantic import Field

from app.db.models.task_model import PriorityLevel, ResourceType, StatusTask
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    """Class untuk membuat tugas baru."""

    name: str = Field(default="Untitled Task")
    description: str | None = Field(default=None)
    resource_type: ResourceType = Field(default=ResourceType.TASK)
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int = Field(default=0)
    due_date: datetime.datetime | None = Field(default=None)
    start_date: datetime.datetime | None = Field(default=None)
    estimated_duration: int | None = Field(default=None)


class TaskUpdate(BaseSchema):
    """Class untuk memperbarui tugas yang ada."""

    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int | None = Field(default=None)
    due_date: datetime.datetime | None = Field(default=None)
    start_date: datetime.datetime | None = Field(default=None)
    estimated_duration: int | None = Field(default=None)


class TaskResponse(BaseSchema):
    id: int
    name: str = Field(default="Untitled Task")
    description: str | None = Field(default=None)
    resource_type: ResourceType = Field(default=ResourceType.TASK)
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int | None = Field(default=None)
    due_date: datetime.datetime | None = Field(default=None)
    start_date: datetime.datetime | None = Field(default=None)
    estimated_duration: int | None = Field(default=None)

    # subtask
    subtask: list["TaskResponse"] = Field(
        default_factory=list, description="Daftar subtask dari tugas ini."
    )
