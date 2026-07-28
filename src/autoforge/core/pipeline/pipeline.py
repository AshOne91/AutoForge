from abc import ABC, abstractmethod


class Pipeline(ABC):
    """
    Pipeline Interface
    """

    @abstractmethod
    def run(self):
        """
        Pipeline 실행
        """
        pass