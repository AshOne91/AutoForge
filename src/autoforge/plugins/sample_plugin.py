from autoforge.core.context.plugin_context import PluginContext
from autoforge.core.plugin.base import Plugin
from autoforge.core.plugin.metadata import PluginMetadata

from autoforge.models.plugin_result import PluginResult

class SamplePlugin(Plugin):

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="Sample Plugin",
            version="0.1.0",
            description="Sample plugin",
            author="Kwon"
        )

    def initialize(self):
        print("Plugin initialized")

    def execute(self, context: PluginContext) -> PluginResult:
        print("Plugin executed")
        return PluginResult(
        success=True,
        message="Sample Plugin executed."
        )