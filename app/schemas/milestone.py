from pydantic import Field

from app.db.models.task_model import StatusTask
from app.schemas.base import BaseSchema


class MileStoneCreate(BaseSchema):
    name: str = Field(default="Untitled Task")
    # description: str | None = Field(default=None)
    status: StatusTask | None = Field(default=StatusTask.IN_PROGRESS)
    # priority: PriorityLevel | None = Field(default=None)
    display_order: int = Field(default=0)
    # due_date: datetime.datetime | None = Field(default=None)
    # start_date: datetime.datetime | None = Field(default=None)
    # estimated_duration: int | None = Field(default=None)
