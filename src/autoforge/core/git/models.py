from dataclasses import dataclass
from pathlib import Path


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
