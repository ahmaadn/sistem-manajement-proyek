from dataclasses import dataclass

from app.core.domain.bus import DomainEvent


@dataclass(frozen=True, kw_only=True)
class UserRoleAssignedEvent(DomainEvent):
    user_id: int
    role_name: str
