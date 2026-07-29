import asyncio

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
