import asyncio

from autoforge.core.task.manager import TaskManager
from autoforge.core.task.task import Task


class HelloTask(Task):

    async def execute(self):
        print("Hello AutoForge")


async def main():

    manager = TaskManager()

    manager.register(
        "hello",
        HelloTask(),
    )

    await manager.execute("hello")


asyncio.run(main())