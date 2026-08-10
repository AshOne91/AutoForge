import asyncio
from dataclasses import FrozenInstanceError

import pytest

from autoforge.core.event import (
    Event,
    EventBus,
    EventDispatchError,
    EventHandler,
    HandlerFailurePolicy,
)


class SampleEvent(Event):
    pass


class RecordingHandler(EventHandler):
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def handle(self, event: Event) -> None:
        self.events.append(event)


class FailingHandler(EventHandler):
    async def handle(self, event: Event) -> None:
        del event
        raise RuntimeError("handler failed")


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


def test_base_event_subscription_observes_subclass_events() -> None:
    bus = EventBus()
    handler = RecordingHandler()
    event = SampleEvent()

    bus.subscribe(Event, handler)

    asyncio.run(bus.publish(event))

    assert handler.events == [event]
    assert bus.handlers(SampleEvent) == [handler]


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


def test_critical_failure_is_raised_after_all_handlers_finish() -> None:
    bus = EventBus()
    failing = FailingHandler()
    recording = RecordingHandler()
    event = SampleEvent()
    bus.subscribe(SampleEvent, failing)
    bus.subscribe(SampleEvent, recording)

    with pytest.raises(EventDispatchError) as raised:
        asyncio.run(bus.publish(event))

    assert recording.events == [event]
    assert raised.value.result.handler_count == 2
    assert len(raised.value.result.critical_failures) == 1
    assert raised.value.result.failures[0].handler_type == "FailingHandler"


def test_observational_failure_is_reported_without_failing_publish() -> None:
    bus = EventBus()
    failing = FailingHandler()
    recording = RecordingHandler()
    event = SampleEvent()
    bus.subscribe(
        SampleEvent,
        failing,
        failure_policy=HandlerFailurePolicy.OBSERVATIONAL,
    )
    bus.subscribe(SampleEvent, recording)

    result = asyncio.run(bus.publish(event))

    assert recording.events == [event]
    assert not result.succeeded
    assert result.critical_failures == ()
    assert result.failures[0].failure_policy is HandlerFailurePolicy.OBSERVATIONAL


def test_duplicate_subscription_preserves_original_failure_policy() -> None:
    bus = EventBus()
    handler = RecordingHandler()
    bus.subscribe(
        SampleEvent,
        handler,
        failure_policy=HandlerFailurePolicy.OBSERVATIONAL,
    )
    bus.subscribe(SampleEvent, handler)

    subscriptions = bus.subscriptions(SampleEvent)

    assert len(subscriptions) == 1
    assert subscriptions[0].failure_policy is HandlerFailurePolicy.OBSERVATIONAL
