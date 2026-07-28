from autoforge.core.config import config
from autoforge.core.context.plugin_context import PluginContext
from autoforge.core.plugin.manager import PluginManager

from autoforge.plugins.sample_plugin import SamplePlugin


manager = PluginManager()

manager.register(SamplePlugin())

print(manager.list_plugins())

context = PluginContext(config=config)

result = manager.execute("Sample Plugin", context)

print(result.success)
print(result.message)
print(manager.exists("Sample Plugin"))

manager.unregister("Sample Plugin")

print(manager.exists("Sample Plugin"))