import os
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from autoforge.core.git import (
    GitCheckoutPolicy,
    GitCheckoutRequest,
    GitCheckoutResult,
)
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.process.runner import AsyncioProcessRunner
from autoforge.services.validation import ProcessResult

_COMMIT_SHA = re.compile(r"[0-9a-fA-F]{40,64}")
_FORBIDDEN_REF_CHARACTERS = frozenset(" ~^:?*[\\")


class GitProviderError(RuntimeError):
    pass


class SubprocessGitProvider:
    def __init__(
        self,
        *,
        policy: GitCheckoutPolicy,
        process_runner: AsyncioProcessRunner | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self._policy = policy
        self._runner = process_runner or AsyncioProcessRunner()
        self._timeout_seconds = timeout_seconds

    async def checkout(
        self,
        request: GitCheckoutRequest,
        *,
        workspace: Workspace,
    ) -> GitCheckoutResult:
        repository_url, local = self._validate_repository(request.repository_url)
        revision = _validate_revision(request.revision)
        repository_path = workspace.resolve(request.destination)
        if repository_path.exists():
            raise ValueError("Git checkout destination must not already exist")
        repository_path.parent.mkdir(parents=True, exist_ok=True)
        protocol = "always" if local else "never"
        environment = {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_TERMINAL_PROMPT": "0",
            "GCM_INTERACTIVE": "Never",
        }
        clone = await self._runner.run(
            (
                "git",
                "-c",
                f"protocol.file.allow={protocol}",
                "clone",
                "--no-checkout",
                "--",
                repository_url,
                str(repository_path),
            ),
            cwd=workspace.root,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("clone", clone)
        resolved = await self._runner.run(
            ("git", "rev-parse", "--verify", f"{revision}^{{commit}}"),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("resolve revision", resolved)
        commit_sha = resolved.stdout.strip()
        if _COMMIT_SHA.fullmatch(commit_sha) is None:
            raise GitProviderError("Git returned an invalid commit SHA")
        checkout = await self._runner.run(
            (
                "git",
                "-c",
                "advice.detachedHead=false",
                "checkout",
                "--detach",
                "--force",
                commit_sha,
            ),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("checkout", checkout)
        status = await self._runner.run(
            ("git", "status", "--porcelain=v1", "--untracked-files=no"),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("verify checkout", status)
        if status.stdout.strip():
            raise GitProviderError("Git checkout is not clean")
        return GitCheckoutResult(
            repository_path=repository_path,
            commit_sha=commit_sha.lower(),
            remote_url=repository_url,
        )

    def _validate_repository(self, value: str) -> tuple[str, bool]:
        if not value or value != value.strip() or value.startswith("-"):
            raise ValueError("repository_url is invalid")
        parsed = urlsplit(value)
        is_windows_path = (
            len(value) >= 3
            and value[1] == ":"
            and value[2] in {"/", "\\"}
        ) or value.startswith("\\\\")
        if parsed.scheme and not is_windows_path:
            if parsed.scheme not in {"https", "ssh"}:
                raise ValueError("Only https and canonical ssh URLs are allowed")
            if parsed.query or parsed.fragment or parsed.password is not None:
                raise ValueError("Repository URL credentials, query and fragment are forbidden")
            if parsed.scheme == "https" and parsed.username is not None:
                raise ValueError("HTTPS repository URL must not contain credentials")
            if parsed.scheme == "ssh" and parsed.username not in {None, "git"}:
                raise ValueError("SSH repository user must be 'git'")
            host = (parsed.hostname or "").lower()
            if not host or host not in {item.lower() for item in self._policy.allowed_hosts}:
                raise ValueError("Repository host is not allowed")
            path = PurePosixPath(unquote(parsed.path))
            if not path.parts or ".." in path.parts:
                raise ValueError("Repository URL path is invalid")
            return value, False

        candidate = Path(value).resolve()
        if not any(_is_within(candidate, root) for root in self._policy.allowed_local_roots):
            raise ValueError("Local repository path is not allowed")
        if not candidate.is_dir():
            raise ValueError("Local repository path does not exist")
        return str(candidate), True


def _validate_revision(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or len(value) > 255
        or value.startswith("-")
        or value.endswith((".", "/"))
        or ".." in value
        or "@{" in value
        or "//" in value
        or any(character in _FORBIDDEN_REF_CHARACTERS for character in value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError("Git revision is invalid")
    return value


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root.resolve())
    except ValueError:
        return False
    return True


def _require_success(operation: str, result: ProcessResult) -> None:
    if result.succeeded:
        return
    detail = result.stderr.strip() or result.error or "unknown Git error"
    raise GitProviderError(f"Git {operation} failed: {detail[:2000]}")
