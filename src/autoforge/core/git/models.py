from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from autoforge.core.secret import SecretReference
from autoforge.core.workspace import validate_workspace_relative_path


@dataclass(frozen=True, slots=True)
class GitCredentialReference:
    username: str
    password: SecretReference

    def __post_init__(self) -> None:
        if (
            not self.username
            or self.username != self.username.strip()
            or len(self.username) > 254
            or any(ord(character) < 32 for character in self.username)
        ):
            raise ValueError("Git credential username is invalid")


@dataclass(frozen=True, slots=True)
class GitCheckoutRequest:
    repository_url: str
    revision: str
    destination: str = "repository"
    credential: GitCredentialReference | None = None


@dataclass(frozen=True, slots=True)
class GitCheckoutPolicy:
    allowed_hosts: frozenset[str]
    allowed_local_roots: tuple[Path, ...] = ()
    allowed_push_branch_prefixes: tuple[str, ...] = ("autoforge/",)
    protected_branches: frozenset[str] = frozenset({"main", "master"})

    def __post_init__(self) -> None:
        if not self.allowed_push_branch_prefixes or any(
            not prefix
            or prefix != prefix.strip()
            or not prefix.endswith("/")
            or prefix.startswith(("-", "/"))
            for prefix in self.allowed_push_branch_prefixes
        ):
            raise ValueError("Git push branch prefixes are invalid")
        if any(not branch.strip() for branch in self.protected_branches):
            raise ValueError("Git protected branch names are invalid")


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


@dataclass(frozen=True, slots=True)
class GitPushRequest:
    expected_commit_sha: str
    branch_name: str
    repository_destination: str = "repository"
    remote_name: str = "origin"
    credential: GitCredentialReference | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "repository_destination",
            validate_workspace_relative_path(
                self.repository_destination
            ).as_posix(),
        )


@dataclass(frozen=True, slots=True)
class GitPushResult:
    commit_sha: str
    branch_name: str
    remote_url: str
    pushed: bool
