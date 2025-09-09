import datetime
from typing import Optional

from app.schemas.base import BaseSchema


class AttachmentCreate(BaseSchema):
    task_id: int
    comment_id: Optional[int] = None
    file_name: str
    file_size: str


class AttachmentRead(BaseSchema):
    id: int
    task_id: int
    comment_id: Optional[int] = None
    mime_type: str
    file_name: str
    file_path: str
    file_size: str
    user_id: int
    created_at: datetime.datetime


class AttachmentLinkCreate(BaseSchema):
    link: str
    file_name: str
