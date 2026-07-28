from autoforge.core.config import config
from autoforge.core.context.plugin_context import PluginContext
from autoforge.core.plugin.manager import PluginManager

from autoforge.plugins.sample_plugin import SamplePlugin


manager = PluginManager()

manager.register(SamplePlugin())

print(manager.list_plugins())

context = PluginContext(config=config)

manager.execute("Sample Plugin", context)