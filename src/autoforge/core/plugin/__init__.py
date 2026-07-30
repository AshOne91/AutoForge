from autoforge.core.plugin.base import Plugin
from autoforge.core.plugin.generator import (
    GeneratorPluginAdapter,
    GeneratorPluginRegistry,
)
from autoforge.core.plugin.loader import (
    PLUGIN_MANIFEST_FILENAME,
    PluginCandidate,
    PluginLoader,
    PluginLoaderError,
)
from autoforge.core.plugin.metadata import (
    CURRENT_PLUGIN_API_VERSION,
    PluginCapability,
    PluginDependency,
    PluginMetadata,
    PluginPermission,
    validate_plugin_api_version,
)

__all__ = [
    "CURRENT_PLUGIN_API_VERSION",
    "PLUGIN_MANIFEST_FILENAME",
    "GeneratorPluginAdapter",
    "GeneratorPluginRegistry",
    "Plugin",
    "PluginCandidate",
    "PluginCapability",
    "PluginDependency",
    "PluginLoader",
    "PluginLoaderError",
    "PluginMetadata",
    "PluginPermission",
    "validate_plugin_api_version",
]
