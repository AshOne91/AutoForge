from dataclasses import dataclass, field


@dataclass(slots=True)
class PluginMetadata:
    """
    Plugin Manifest
    """

    name: str

    version: str

    description: str = ""

    author: str = ""

    dependencies: list[str] = field(default_factory=list)
