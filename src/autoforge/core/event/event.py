from dataclasses import dataclass, field
from datetime import UTC
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True)
class Event:
    """
    모든 Event의 부모 클래스
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))