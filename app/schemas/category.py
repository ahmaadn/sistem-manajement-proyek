from app.schemas.base import BaseSchema


class CategoryCreate(BaseSchema):
    name: str
    description: str | None = None


class CategoryUpdate(BaseSchema):
    name: str | None = None
    description: str | None = None


class CategoryRead(BaseSchema):
    id: int
    project_id: int
    name: str
    description: str | None
