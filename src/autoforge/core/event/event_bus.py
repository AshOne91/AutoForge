import asyncio
from collections import defaultdict

from autoforge.core.event.event import Event
from autoforge.core.event.handler import EventHandler


class EventBus:
    """
    Async Event Bus

    Event -> Handler를 비동기로 연결한다.
    """

    def __init__(self):
        self._subscriptions: dict[type[Event], list[EventHandler]] = defaultdict(list)

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> None:
        """
        Event Handler 등록
        """

        if handler not in self._subscriptions[event_type]:
            self._subscriptions[event_type].append(handler)

    def unsubscribe(
        self,
        event_type: type[Event],
        handler: EventHandler,
    ) -> None:
        """
        Event Handler 제거
        """

        if handler in self._subscriptions[event_type]:
            self._subscriptions[event_type].remove(handler)

    def handlers(
        self,
        event_type: type[Event],
    ) -> list[EventHandler]:
        """
        등록된 Handler 조회
        """

        return self._subscriptions[event_type]

    async def publish(
        self,
        event: Event,
    ) -> None:
        """
        Event 발행
        """

        handlers = self.handlers(type(event))

        if not handlers:
            return

        tasks = [
            asyncio.create_task(
                handler.handle(event)
            )
            for handler in handlers
        ]

        await asyncio.gather(*tasks)