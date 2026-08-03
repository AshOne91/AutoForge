from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from autoforge.core.workspace import validate_workspace_relative_path


@dataclass(frozen=True, slots=True)
class GitCheckoutRequest:
    repository_url: str
    revision: str
    destination: str = "repository"


@dataclass(frozen=True, slots=True)
class GitCheckoutPolicy:
    allowed_hosts: frozenset[str]
    allowed_local_roots: tuple[Path, ...] = ()


@dataclass(frozen=True, slots=True)
class GitCheckoutResult:
    repository_path: Path
    commit_sha: str
    remote_url: str


@dataclass(frozen=True, slots=True)
class GitCommitRequest:
    expected_base_sha: str
    branch_name: str
    message: str
    author_name: str
    author_email: str
    allowed_paths: tuple[PurePosixPath, ...]
    repository_destination: str = "repository"
    signing_key: str | None = None

    def __post_init__(self) -> None:
        normalized = tuple(
            validate_workspace_relative_path(path) for path in self.allowed_paths
        )
        if not normalized:
            raise ValueError("Git commit allowed_paths must not be empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("Git commit allowed_paths must be unique")
        object.__setattr__(self, "allowed_paths", normalized)
        object.__setattr__(
            self,
            "repository_destination",
            validate_workspace_relative_path(
                self.repository_destination
            ).as_posix(),
        )


@dataclass(frozen=True, slots=True)
class GitCommitResult:
    commit_sha: str
    branch_name: str | None
    changed_paths: tuple[PurePosixPath, ...]
    commit_created: bool
