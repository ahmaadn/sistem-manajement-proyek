from datetime import datetime

from pydantic import Field

from app.schemas.attachment import AttachmentResponse
from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    task_id: int = Field(..., description="ID tugas")
    content: str = Field(..., description="Isi komentar")


class CommentResponse(BaseSchema):
    id: int
    task_id: int
    user_id: int
    content: str
    created_at: datetime


class CommentWithAttachmentResponse(CommentResponse):
    attachments: list[AttachmentResponse] = Field(default_factory=list)
