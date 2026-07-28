from abc import ABC, abstractmethod


class Plugin(ABC):
    """
    모든 AutoForge Plugin의 부모 클래스
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Plugin 이름"""

    @property
    @abstractmethod
    def version(self) -> str:
        """Plugin 버전"""

    @abstractmethod
    def initialize(self):
        """Plugin 초기화"""

    @abstractmethod
    def execute(self):
        """Plugin 실행"""