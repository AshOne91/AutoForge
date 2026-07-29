from dataclasses import dataclass

from autoforge.core.config import ConfigManager


@dataclass
class PluginContext:
    """
    Plugin 실행 시 전달되는 공통 Context
    """

    config: ConfigManager
