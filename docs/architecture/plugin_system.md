# Plugin System

Plugin

↓

PluginManager

↓

PluginContext

↓

PluginResult

Plugins are isolated.

Plugins never access Git directly.

Plugins never modify other plugins.

Plugins communicate only through Pipeline.