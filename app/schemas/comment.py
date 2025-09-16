from datetime import datetime
from typing import Literal, Union

from pydantic import Field

from app.schemas.attachment import AttachmentRead
from app.schemas.audit import TaskAuditSchema
from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    task_id: int = Field(..., description="ID tugas")
    content: str = Field(..., description="Isi komentar")


class CommentRead(BaseSchema):
    id: int
    task_id: int
    user_id: int
    content: str
    created_at: datetime


class CommentDetail(CommentRead):
    profile_url: str | None = None
    user_name: str | None = None
    attachments: list[AttachmentRead] = Field(default_factory=list)


class CommentWithAuditsRead(BaseSchema):
    type: Literal["comment", "audit"]
    data: Union[CommentDetail, TaskAuditSchema]
