import asyncio
from collections import defaultdict

from autoforge.core.event.event import Event
from autoforge.core.event.handler import EventHandler


class EventBus:
    """Generic in-process asynchronous event dispatcher."""

    def __init__(self) -> None:
        self._subscriptions: dict[type[Event], list[EventHandler[Event]]] = defaultdict(
            list
        )

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler[Event],
    ) -> None:
        if handler not in self._subscriptions[event_type]:
            self._subscriptions[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: type[Event],
        handler: EventHandler[Event],
    ) -> None:
        subscriptions = self._subscriptions.get(event_type)
        if subscriptions is None or handler not in subscriptions:
            return
        subscriptions.remove(handler)
        if not subscriptions:
            del self._subscriptions[event_type]

    def handlers(self, event_type: type[Event]) -> list[EventHandler[Event]]:
        """Return a snapshot so callers cannot mutate bus subscriptions."""

        return list(self._subscriptions.get(event_type, ()))

    async def publish(self, event: Event) -> None:
        handlers = self.handlers(type(event))
        if not handlers:
            return
        await asyncio.gather(*(handler.handle(event) for handler in handlers))
