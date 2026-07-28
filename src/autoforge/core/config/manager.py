from autoforge.core.config.loader import ConfigLoader


class ConfigManager:

    def __init__(self):
        self._settings = ConfigLoader.load()

    @property
    def settings(self):
        return self._settings


config = ConfigManager()