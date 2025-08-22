from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Base schema for all schemas."""

    model_config = ConfigDict(from_attributes=True)


class MessageSuccessSchema(BaseSchema):
    """Schema for successful messages."""

    message: str
