from autoforge.core.plugin.base import Plugin
from autoforge.models.plugin_result import PluginResult

from .manifest import PLUGIN_METADATA


class SamplePlugin(Plugin):

    @property
    def metadata(self):
        return PLUGIN_METADATA

    def initialize(self):
        print("Sample Plugin Initialized")

    def execute(self, context):

        print("Sample Plugin Executed")

        return PluginResult(
            success=True,
            message="Success",
        )