from app.schemas.base import BaseSchema


class AuthToken(BaseSchema):
    access_token: str
    token_type: str = "bearer"
