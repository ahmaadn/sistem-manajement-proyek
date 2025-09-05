import datetime
from typing import Optional

from app.schemas.base import BaseSchema


class AttachmentBase(BaseSchema):
    task_id: int
    comment_id: Optional[int] = None


class AttachmentCreate(AttachmentBase):
    file_name: str
    file_size: str


class AttachmentRead(AttachmentBase):
    id: int
    file_name: str
    file_path: str
    file_size: str
    user_id: int
    created_at: datetime.datetime
