from dataclasses import dataclass
from pathlib import Path, PurePosixPath


def validate_workspace_relative_path(value: object) -> PurePosixPath:
    path = PurePosixPath(str(value))
    if path.is_absolute():
        raise ValueError("Workspace 경로는 상대 경로여야 합니다.")
    if path.parts and ":" in path.parts[0]:
        raise ValueError("Workspace 경로에는 드라이브를 지정할 수 없습니다.")
    if not path.parts or path == PurePosixPath("."):
        raise ValueError("Workspace 경로는 비어 있을 수 없습니다.")
    if ".." in path.parts:
        raise ValueError("Workspace 경로에는 '..'을 사용할 수 없습니다.")
    if "\\" in str(value):
        raise ValueError("Workspace 경로에는 역슬래시를 사용할 수 없습니다.")
    return path


@dataclass(frozen=True, slots=True)
class Workspace:
    root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())

    def resolve(self, relative_path: str | PurePosixPath) -> Path:
        validated_path = validate_workspace_relative_path(relative_path)
        candidate = self.root.joinpath(*validated_path.parts).resolve()

        try:
            candidate.relative_to(self.root)
        except ValueError as error:
            raise ValueError(
                "해석된 경로가 Workspace 외부를 가리킵니다."
            ) from error
        return candidate

    def contains(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.root)
        except ValueError:
            return False
        return True
