from app.db.models.role_model import Role
from app.schemas.base import BaseSchema
from app.schemas.user import User


class AdminDashboardResponse(BaseSchema):
    top_users: list[User]
    role_counts: dict[Role, int]
