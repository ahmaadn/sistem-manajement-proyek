from app.schemas.base import BaseSchema


class TokenAuth(BaseSchema):
    access_token: str
    token_type: str = "bearer"
