from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PluginResult:
    """
    Plugin 실행 결과
    """

    success: bool

    message: str = ""

    generated_files: list[Path] = field(default_factory=list)