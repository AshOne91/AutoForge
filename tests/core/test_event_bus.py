import asyncio
from dataclasses import FrozenInstanceError

import pytest

from autoforge.core.event.event import Event
from autoforge.core.event.event_bus import EventBus
from autoforge.core.event.handler import EventHandler


class SampleEvent(Event):
    pass


class RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


def test_publish_event_to_subscribed_handlers() -> None:
    bus = EventBus()
    first_handler = RecordingHandler()
    second_handler = RecordingHandler()
    event = SampleEvent()

    bus.subscribe(SampleEvent, first_handler)
    bus.subscribe(SampleEvent, second_handler)

    asyncio.run(bus.publish(event))

    assert first_handler.events == [event]
    assert second_handler.events == [event]
    assert bus.handlers(SampleEvent) == [first_handler, second_handler]


def test_handlers_returns_snapshot_and_unsubscribe_removes_handler() -> None:
    bus = EventBus()
    handler = RecordingHandler()
    bus.subscribe(SampleEvent, handler)

    snapshot = bus.handlers(SampleEvent)
    snapshot.clear()

    assert bus.handlers(SampleEvent) == [handler]
    bus.unsubscribe(SampleEvent, handler)
    assert bus.handlers(SampleEvent) == []


def test_event_metadata_is_immutable_and_timezone_aware() -> None:
    event = SampleEvent(job_id="job-1", producer="test")

    assert event.event_type == "SampleEvent"
    assert event.correlation_id == event.event_id
    assert event.created_at.utcoffset() is not None
    with pytest.raises(FrozenInstanceError):
        event.job_id = "other"  # type: ignore[misc]


def test_event_rejects_naive_created_at() -> None:
    from datetime import UTC, datetime

    with pytest.raises(ValueError, match="timezone-aware"):
        SampleEvent(created_at=datetime.now(UTC).replace(tzinfo=None))
