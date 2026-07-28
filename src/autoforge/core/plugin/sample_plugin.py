from autoforge.core.plugin.base import Plugin


class SamplePlugin(Plugin):

    @property
    def name(self):
        return "Sample"

    @property
    def version(self):
        return "0.0.1"

    def initialize(self):
        print("Plugin Initialized")

    def execute(self):
        print("Plugin Executed")