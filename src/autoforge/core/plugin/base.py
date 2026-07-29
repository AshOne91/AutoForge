from abc import ABC, abstractmethod

from autoforge.core.context.plugin_context import PluginContext
from autoforge.core.plugin.metadata import PluginMetadata
from autoforge.models.plugin_result import PluginResult


class Plugin(ABC):
    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        플러그인 정보
        """

    @abstractmethod
    def initialize(self) -> None:
        """
        초기화
        """

    @abstractmethod
    def execute(self, context: PluginContext) -> PluginResult:
        """
        실행
        """
