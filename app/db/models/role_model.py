from enum import StrEnum

from sqlalchemy import Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.models.mixin import TimeStampMixin


class Role(StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    TEAM_MEMBER = "team_member"


class UserRole(Base, TimeStampMixin):
    __tablename__ = "user_role"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, unique=True)
    role: Mapped[Role] = mapped_column(
        Enum(Role, name="role"), nullable=False, default=Role.TEAM_MEMBER
    )
