import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, declared_attr, mapped_column


class CreateStampMixin:
    if TYPE_CHECKING:
        created_at: Mapped[datetime.datetime]
    else:

        @declared_attr
        def created_at(cls) -> Mapped[datetime.datetime]:  # noqa: N805
            return mapped_column(
                DateTime(True),
                nullable=False,
                default=datetime.datetime.now(datetime.UTC),
                server_default=func.now(),
            )


class UpdateStampMixin:
    if TYPE_CHECKING:
        updated_at: Mapped[datetime.datetime]
    else:

        @declared_attr
        def updated_at(cls) -> Mapped[datetime.datetime]:  # noqa: N805
            return mapped_column(
                DateTime(True),
                nullable=False,
                default=datetime.datetime.now(datetime.UTC),
                onupdate=func.now(),
            )


class TimeStampMixin(CreateStampMixin, UpdateStampMixin):
    pass


class SoftDeleteMixin:
    deleted_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(True), default=None
    )

    @property
    def is_deleted(self) -> bool:
        """Return True jika objek sudah dihapus (deleted_at tidak None)."""
        return self.deleted_at is not None
