import asyncio

from autoforge.core.event.event import Event
from autoforge.core.event.event_bus import EventBus
from autoforge.core.event.handler import EventHandler


class SampleEvent(Event):
    pass


class PrintHandler(EventHandler):

    async def handle(self, event):

        print("Print Handler")


class LoggerHandler(EventHandler):

    async def handle(self, event):

        print("Logger Handler")


async def main():

    bus = EventBus()

    bus.subscribe(
        SampleEvent,
        PrintHandler(),
    )

    bus.subscribe(
        SampleEvent,
        LoggerHandler(),
    )

    await bus.publish(
        SampleEvent()
    )


asyncio.run(main())