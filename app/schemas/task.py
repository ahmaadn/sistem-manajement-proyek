import datetime

from pydantic import Field

from app.db.models.task_model import PriorityLevel, ResourceType, StatusTask
from app.schemas.base import BaseSchema


class TaskBase(BaseSchema):
    name: str = Field(default="Untitled Task")
    description: str | None = Field()
    resource_type: ResourceType = Field(default=ResourceType.TASK)
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int | None = Field(default=None)
    due_date: datetime.datetime | None = Field(default=None)
    start_date: datetime.datetime | None = Field(default=None)
    estimated_duration: int | None = Field(default=None)


class TaskCreate(BaseSchema):
    """Class untuk membuat tugas baru."""

    name: str = Field(default="Untitled Task")
    description: str | None = Field(default=None)
    resource_type: ResourceType = Field(default=ResourceType.TASK)
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    # display_order: int | None = Field(default=None)
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
