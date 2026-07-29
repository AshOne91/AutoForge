from abc import ABC, abstractmethod


class Pipeline(ABC):
    """
    Pipeline Interface
    """

    @abstractmethod
    def run(self) -> None:
        """
        Pipeline 실행
        """
        ...
