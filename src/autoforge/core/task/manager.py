from autoforge.core.task.task import Task


class TaskManager:

    def __init__(self):
        self._tasks: dict[str, Task] = {}

    def register(self, name: str, task: Task):

        if name in self._tasks:
            raise ValueError(f"{name} already registered.")

        self._tasks[name] = task

    def get(self, name: str):

        return self._tasks[name]

    async def execute(self, name: str):

        task = self.get(name)

        return await task.execute()