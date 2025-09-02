from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.base import BaseSchema


class MilestoneBase(BaseSchema):
    title: str = Field(..., max_length=255)


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseSchema):
    title: Optional[str] = Field(None, max_length=255)


class MilestoneResponse(BaseSchema):
    id: int
    project_id: int
    title: str
    display_order: int
    created_at: datetime
    updated_at: datetime | None = None
