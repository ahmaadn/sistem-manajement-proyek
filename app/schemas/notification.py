from datetime import datetime

from app.schemas.base import BaseSchema


class NotificationRead(BaseSchema):
    id: int
    recipient_id: int

    type: str = ""
    message: str = ""
    created_at: datetime

    actor_id: int
    actor_name: str = ""
    actor_profile_url: str | None = None

    project_id: int
    project_title: str | None = None

    task_id: int | None = None
    task_name: str | None = None

    is_read: bool = False
    read_at: datetime | None = None
