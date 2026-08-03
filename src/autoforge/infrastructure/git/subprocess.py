import os
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from autoforge.core.git import (
    GitCheckoutPolicy,
    GitCheckoutRequest,
    GitCheckoutResult,
    GitCommitRequest,
    GitCommitResult,
)
from autoforge.core.workspace import Workspace, validate_workspace_relative_path
from autoforge.infrastructure.process.runner import AsyncioProcessRunner
from autoforge.services.validation import ProcessResult

_COMMIT_SHA = re.compile(r"[0-9a-fA-F]{40,64}")
_SIGNING_KEY = re.compile(r"[0-9a-fA-F]{16,64}")
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
        environment = _git_environment()
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

    async def commit_validated(
        self,
        request: GitCommitRequest,
        *,
        workspace: Workspace,
    ) -> GitCommitResult:
        repository_path = workspace.resolve(request.repository_destination)
        if not (repository_path / ".git").is_dir():
            raise ValueError("Git commit destination is not a repository")
        expected_base = _validate_commit_sha(request.expected_base_sha)
        branch_name = _validate_branch_name(request.branch_name)
        message = _validate_commit_message(request.message)
        author_name = _validate_identity("author_name", request.author_name)
        author_email = _validate_identity("author_email", request.author_email)
        signing_key = _validate_signing_key(request.signing_key)
        environment = _git_environment()

        head = await self._runner.run(
            ("git", "rev-parse", "--verify", "HEAD"),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("verify commit base", head)
        actual_base = _validate_commit_sha(head.stdout.strip())
        if actual_base.lower() != expected_base.lower():
            raise GitProviderError("Git HEAD does not match the expected base commit")

        changed_paths = await self._changed_paths(repository_path, environment)
        allowed_paths = frozenset(request.allowed_paths)
        unexpected = sorted(set(changed_paths) - allowed_paths)
        if unexpected:
            rendered = ", ".join(path.as_posix() for path in unexpected)
            raise GitProviderError(f"Git found changes outside the allowlist: {rendered}")
        if not changed_paths:
            return GitCommitResult(
                commit_sha=actual_base.lower(),
                branch_name=None,
                changed_paths=(),
                commit_created=False,
            )

        check_branch = await self._runner.run(
            ("git", "check-ref-format", "--branch", branch_name),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("validate branch", check_branch)
        create_branch = await self._runner.run(
            ("git", "switch", "--create", branch_name),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("create branch", create_branch)
        path_arguments = tuple(path.as_posix() for path in changed_paths)
        stage = await self._runner.run(
            ("git", "add", "--", *path_arguments),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("stage validated changes", stage)
        staged = await self._runner.run(
            ("git", "diff", "--cached", "--name-only", "-z"),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("verify staged changes", staged)
        staged_paths = _parse_nul_paths(staged.stdout)
        if staged_paths != changed_paths:
            raise GitProviderError("Git staged paths differ from validated changes")

        signing_argument = (
            f"--gpg-sign={signing_key}" if signing_key else "--no-gpg-sign"
        )
        commit = await self._runner.run(
            (
                "git",
                "-c",
                f"user.name={author_name}",
                "-c",
                f"user.email={author_email}",
                "commit",
                signing_argument,
                "--message",
                message,
            ),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("commit validated changes", commit)
        committed = await self._runner.run(
            ("git", "rev-parse", "--verify", "HEAD"),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("resolve created commit", committed)
        commit_sha = _validate_commit_sha(committed.stdout.strip()).lower()
        return GitCommitResult(
            commit_sha=commit_sha,
            branch_name=branch_name,
            changed_paths=changed_paths,
            commit_created=True,
        )

    async def _changed_paths(
        self, repository_path: Path, environment: dict[str, str]
    ) -> tuple[PurePosixPath, ...]:
        status = await self._runner.run(
            ("git", "status", "--porcelain=v1", "-z", "--untracked-files=all"),
            cwd=repository_path,
            timeout_seconds=self._timeout_seconds,
            environment=environment,
        )
        _require_success("inspect changes", status)
        return _parse_status_paths(status.stdout)

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


def _validate_commit_sha(value: str) -> str:
    if _COMMIT_SHA.fullmatch(value) is None:
        raise ValueError("Git commit SHA is invalid")
    return value


def _validate_branch_name(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or len(value) > 255
        or value.startswith(("-", ".", "/"))
        or value.endswith((".", "/", ".lock"))
        or ".." in value
        or "@{" in value
        or "//" in value
        or "\\" in value
        or any(character in _FORBIDDEN_REF_CHARACTERS for character in value)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError("Git branch name is invalid")
    return value


def _validate_commit_message(value: str) -> str:
    if (
        not value
        or value != value.strip()
        or len(value) > 200
        or "\n" in value
        or "\r" in value
        or any(ord(character) < 32 for character in value)
    ):
        raise ValueError("Git commit message must be a single non-empty line")
    return value


def _validate_identity(field: str, value: str) -> str:
    if (
        not value
        or value != value.strip()
        or len(value) > 254
        or "\n" in value
        or "\r" in value
        or "\0" in value
    ):
        raise ValueError(f"Git {field} is invalid")
    return value


def _validate_signing_key(value: str | None) -> str | None:
    if value is not None and _SIGNING_KEY.fullmatch(value) is None:
        raise ValueError("Git signing_key must be a hexadecimal fingerprint")
    return value


def _parse_status_paths(output: str) -> tuple[PurePosixPath, ...]:
    paths: list[PurePosixPath] = []
    for record in output.split("\0"):
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise GitProviderError("Git returned malformed status output")
        status = record[:2]
        if "R" in status or "C" in status:
            raise GitProviderError("Git rename and copy changes are not allowed")
        paths.append(_validated_git_path(record[3:]))
    if len(paths) != len(set(paths)):
        raise GitProviderError("Git returned duplicate changed paths")
    return tuple(sorted(paths))


def _parse_nul_paths(output: str) -> tuple[PurePosixPath, ...]:
    paths = tuple(
        _validated_git_path(value) for value in output.split("\0") if value
    )
    return tuple(sorted(paths))


def _validated_git_path(value: str) -> PurePosixPath:
    if "\\" in value:
        raise GitProviderError("Git returned a non-POSIX path")
    try:
        return validate_workspace_relative_path(value)
    except ValueError as error:
        raise GitProviderError("Git returned an unsafe changed path") from error


def _git_environment() -> dict[str, str]:
    return {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_TERMINAL_PROMPT": "0",
        "GCM_INTERACTIVE": "Never",
    }


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
