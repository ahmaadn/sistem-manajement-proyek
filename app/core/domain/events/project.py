from dataclasses import dataclass

from app.core.domain.bus import DomainEvent


@dataclass(frozen=True, kw_only=True)
class ProjectCreatedEvent(DomainEvent):
    user_id: int
    project_id: int
    project_title: str
