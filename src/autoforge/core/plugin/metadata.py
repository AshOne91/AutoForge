from dataclasses import dataclass


@dataclass(frozen=True)
class PluginMetadata:
    """
    플러그인의 기본 정보
    """

    name: str
    version: str
    description: str
    author: str