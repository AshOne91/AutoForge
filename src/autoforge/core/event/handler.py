from abc import ABC, abstractmethod

from autoforge.core.event.event import Event


class EventHandler[TEvent: Event](ABC):
    """Handle one event type without coupling its producer to this consumer."""

    @abstractmethod
    async def handle(self, event: TEvent) -> None: ...
