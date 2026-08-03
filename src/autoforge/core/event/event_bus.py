import asyncio
from collections import defaultdict

from autoforge.core.event.dispatch import (
    EventDispatchError,
    EventDispatchResult,
    EventSubscription,
    HandlerDispatchFailure,
    HandlerFailurePolicy,
)
from autoforge.core.event.event import Event
from autoforge.core.event.handler import EventHandler


class EventBus:
    """Generic in-process asynchronous event dispatcher."""

    def __init__(self) -> None:
        self._subscriptions: dict[type[Event], list[EventSubscription]] = defaultdict(
            list
        )

    def subscribe(
        self,
        event_type: type[Event],
        handler: EventHandler[Event],
        *,
        failure_policy: HandlerFailurePolicy = HandlerFailurePolicy.CRITICAL,
    ) -> None:
        if any(
            subscription.handler is handler
            for subscription in self._subscriptions[event_type]
        ):
            return
        self._subscriptions[event_type].append(
            EventSubscription(handler=handler, failure_policy=failure_policy)
        )

    def unsubscribe(
        self,
        event_type: type[Event],
        handler: EventHandler[Event],
    ) -> None:
        subscriptions = self._subscriptions.get(event_type)
        if subscriptions is None:
            return
        retained = [
            subscription
            for subscription in subscriptions
            if subscription.handler is not handler
        ]
        if retained:
            self._subscriptions[event_type] = retained
        else:
            del self._subscriptions[event_type]

    def handlers(self, event_type: type[Event]) -> list[EventHandler[Event]]:
        """Return a compatible handler snapshot without exposing subscriptions."""

        return [
            subscription.handler for subscription in self.subscriptions(event_type)
        ]

    def subscriptions(self, event_type: type[Event]) -> tuple[EventSubscription, ...]:
        return tuple(self._subscriptions.get(event_type, ()))

    async def publish(self, event: Event) -> EventDispatchResult:
        subscriptions = self.subscriptions(type(event))
        if not subscriptions:
            return EventDispatchResult(event.event_id, 0, ())
        failures = tuple(
            failure
            for failure in await asyncio.gather(
                *(self._invoke(subscription, event) for subscription in subscriptions)
            )
            if failure is not None
        )
        result = EventDispatchResult(event.event_id, len(subscriptions), failures)
        if result.critical_failures:
            raise EventDispatchError(event, result)
        return result

    @staticmethod
    async def _invoke(
        subscription: EventSubscription, event: Event
    ) -> HandlerDispatchFailure | None:
        try:
            await subscription.handler.handle(event)
        # A dispatcher must classify arbitrary handler failures while allowing
        # asyncio cancellation (BaseException) to propagate.
        except Exception as error:  # noqa: BLE001
            return HandlerDispatchFailure(
                handler_type=type(subscription.handler).__name__,
                failure_policy=subscription.failure_policy,
                error=error,
            )
        return None
