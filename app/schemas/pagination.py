from typing import Generic, TypeVar

from app.schemas.base import BaseSchema

_T = TypeVar("_T")


class PaginationSchema(BaseSchema, Generic[_T]):
    """Base schema for pagination."""

    count: int
    items: list[_T]
    curr_page: int
    total_page: int
    next_page: str | None = None
    previous_page: str | None = None


class SimplePaginationSchema(BaseSchema, Generic[_T]):
    """Base schema for pagination."""

    count: int
    data: list[_T]
