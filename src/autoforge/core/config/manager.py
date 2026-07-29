from pathlib import Path

from autoforge.core.config.loader import ConfigLoader
from autoforge.core.config.settings import (
    LoggingConfig,
    PluginConfig,
    ProjectConfig,
    Settings,
    WorkspaceConfig,
)


class ConfigManager:
    """검증된 설정을 명시적으로 주입받아 제공한다."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @classmethod
    def from_file(cls, path: str | Path) -> "ConfigManager":
        return cls(ConfigLoader.load(path))

    @property
    def settings(self) -> Settings:
        return self._settings

    @property
    def project(self) -> ProjectConfig:
        return self._settings.project

    @property
    def workspace(self) -> WorkspaceConfig:
        return self._settings.workspace

    @property
    def logging(self) -> LoggingConfig:
        return self._settings.logging

    @property
    def plugins(self) -> PluginConfig:
        return self._settings.plugins
