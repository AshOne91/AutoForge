from autoforge.core.config.loader import ConfigLoader


class ConfigManager:
    """애플리케이션 전역 설정"""

    def __init__(self):
        self._settings = ConfigLoader.load()

    def __getattr__(self, item):
        return getattr(self._settings, item)


config = ConfigManager()