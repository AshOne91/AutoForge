import asyncio

from autoforge.core.task.manager import TaskManager
from autoforge.core.task.task import Task


class HelloTask(Task):

    def __init__(self) -> None:
        self.executed = False

    async def execute(self) -> str:
        self.executed = True
        return "Hello AutoForge"


def test_register_and_execute_task() -> None:
    manager = TaskManager()
    task = HelloTask()

    manager.register("hello", task)

    result = asyncio.run(manager.execute("hello"))

    assert result == "Hello AutoForge"
    assert task.executed
    assert manager.get("hello") is task
