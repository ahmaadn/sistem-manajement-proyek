from datetime import datetime

from pydantic import Field

from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    task_id: int = Field(..., description="ID tugas")
    content: str = Field(..., description="Isi komentar")


class CommentAttachmentResponse(BaseSchema):
    attachment_id: int
    file_name: str
    file_path: str
    file_size: str
    user_id: int
    created_at: datetime


class CommentResponse(BaseSchema):
    id: int
    task_id: int
    user_id: int
    content: str
    created_at: datetime


class CommentWithAttachmentResponse(CommentResponse):
    attachment: CommentAttachmentResponse | None = None
