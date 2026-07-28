from abc import ABC, abstractmethod

from autoforge.core.execution.context import PluginContext
from autoforge.core.plugin.metadata import PluginMetadata


class Plugin(ABC):

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        플러그인 정보
        """

    @abstractmethod
    def initialize(self):
        """
        초기화
        """

    @abstractmethod
    def execute(self, context: PluginContext):
        """
        실행
        """