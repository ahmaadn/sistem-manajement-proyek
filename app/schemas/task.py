import datetime
from typing import List

from pydantic import Field

from app.db.models.task_model import PriorityLevel, StatusTask
from app.schemas.base import BaseSchema


class TaskCreate(BaseSchema):
    """Class untuk membuat tugas baru."""

    name: str = Field(default="Untitled Task")
    description: str | None = Field(default=None)
    status: StatusTask | None = Field(default=StatusTask.IN_PROGRESS)
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


class TaskRead(BaseSchema):
    id: int
    name: str = Field(default="Untitled Task")
    description: str | None = Field(default=None)
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int | None = Field(default=None)
    due_date: datetime.datetime | None = Field(default=None)
    start_date: datetime.datetime | None = Field(default=None)
    estimated_duration: int | None = Field(default=None)


class SubTaskRead(BaseSchema):
    """Response schema untuk sub-subtask."""

    id: int
    name: str = Field(default="Untitled Task")
    status: StatusTask | None = Field(default=None)
    priority: PriorityLevel | None = Field(default=None)
    display_order: int | None = Field(default=None)
    due_date: datetime.datetime | None = Field(default=None)
    start_date: datetime.datetime | None = Field(default=None)
    estimated_duration: int | None = Field(default=None)


class TaskAttachmentRead(BaseSchema):
    id: int
    file_name: str
    file_size: str
    mime_type: str
    file_path: str
    created_at: datetime.datetime


class TaskAssigneeRead(BaseSchema):
    """Response schema untuk penugasan tugas."""

    user_id: int
    name: str
    email: str
    profile_url: str = Field(..., description="URL profil pengguna")


class TaskDetail(TaskRead):
    """Response schema untuk detail tugas."""

    assignees: List[TaskAssigneeRead] = Field(
        default_factory=list,
        description="Daftar pengguna yang ditugaskan pada tugas ini.",
    )

    sub_tasks: List[SubTaskRead] = Field(
        default_factory=list,
        description="Daftar subtask dari tugas ini.",
    )

    attachments: list[TaskAttachmentRead] = Field(
        default_factory=list,
        description="Daftar lampiran untuk tugas ini.",
    )
