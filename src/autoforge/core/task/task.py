from abc import ABC, abstractmethod


class Task(ABC):
    """
    Pipeline에서 실행되는 최소 단위
    """

    @abstractmethod
    async def execute(self): ...
