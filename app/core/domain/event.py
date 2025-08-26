import datetime
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_on: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    metadata: dict[str, Any] = field(default_factory=dict)
    performed_by: int | None = None

    @property
    def name(self) -> str:
        return self.__class__.__name__

    def dump_model(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def json(self) -> str:
        return str(self.dump_model())
