from app.schemas.base import BaseSchema


class UserInfo(BaseSchema):
    user_id: int
    name: str
    role: str
    email: str
    username: str
    position: str
    work_unit: str
    address: str
