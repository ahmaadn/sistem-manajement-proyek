from dataclasses import dataclass

from app.core.events.bus import DomainEvent


@dataclass(frozen=True)
class ProjectCreatedEvent(DomainEvent):
    user_id: int
    project_id: int
    project_name: str
