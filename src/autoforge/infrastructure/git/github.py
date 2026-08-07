import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import quote, urlsplit

from autoforge.core.git import (
    GitPullRequestPolicy,
    GitPullRequestRequest,
    GitPullRequestResult,
)
from autoforge.core.secret import SecretProvider

_GITHUB_API_VERSION = "2026-03-10"
_REPOSITORY_PART = re.compile(r"[A-Za-z0-9_.-]+")
_FORBIDDEN_REF_CHARACTERS = frozenset(" ~^:?*[\\")


@dataclass(frozen=True, slots=True)
class GitHubApiResponse:
    status_code: int
    json_body: object


class GitHubApiClient(Protocol):
    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        query: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> GitHubApiResponse: ...


class GitHubPullRequestError(RuntimeError):
    pass


class GitHubPullRequestProvider:
    def __init__(
        self,
        *,
        api_client: GitHubApiClient,
        secret_provider: SecretProvider,
        policy: GitPullRequestPolicy | None = None,
    ) -> None:
        self._api_client = api_client
        self._secret_provider = secret_provider
        self._policy = policy or GitPullRequestPolicy()

    async def create_or_get(
        self,
        request: GitPullRequestRequest,
    ) -> GitPullRequestResult:
        owner, repository = _parse_github_repository(request.repository_url)
        _validate_branch(request.head_branch)
        _validate_branch(request.base_branch)
        self._policy.validate_branches(
            head_branch=request.head_branch,
            base_branch=request.base_branch,
        )
        if request.credential is None:
            raise ValueError("GitHub pull request credential is required")
        token = await self._secret_provider.resolve(request.credential)
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token.reveal()}",
            "User-Agent": "AutoForge",
            "X-GitHub-Api-Version": _GITHUB_API_VERSION,
        }
        repository_path = f"/repos/{owner}/{repository}"

        await self._verify_head(
            repository_path=repository_path,
            branch=request.head_branch,
            expected_sha=request.expected_head_sha,
            headers=headers,
        )
        existing = await self._find_open(
            repository_path=repository_path,
            owner=owner,
            request=request,
            headers=headers,
        )
        if existing is not None:
            return existing

        created = await self._api_client.request(
            "POST",
            f"{repository_path}/pulls",
            headers=headers,
            json_body={
                "base": request.base_branch,
                "body": request.body,
                "head": request.head_branch,
                "title": request.title,
            },
        )
        if created.status_code == 422:
            raced = await self._find_open(
                repository_path=repository_path,
                owner=owner,
                request=request,
                headers=headers,
            )
            if raced is not None:
                return raced
            raise GitHubPullRequestError(
                "GitHub rejected pull request creation and no matching pull request exists"
            )
        if created.status_code != 201:
            raise GitHubPullRequestError(
                f"GitHub create pull request failed with status {created.status_code}"
            )
        return _parse_pull_request(created.json_body, request=request, created=True)

    async def _verify_head(
        self,
        *,
        repository_path: str,
        branch: str,
        expected_sha: str,
        headers: Mapping[str, str],
    ) -> None:
        response = await self._api_client.request(
            "GET",
            f"{repository_path}/git/ref/heads/{quote(branch, safe='')}",
            headers=headers,
        )
        if response.status_code != 200:
            raise GitHubPullRequestError(
                f"GitHub get reference failed with status {response.status_code}"
            )
        payload = _require_mapping(response.json_body, "reference")
        reference_object = _require_mapping(payload.get("object"), "reference object")
        actual_sha = reference_object.get("sha")
        if not isinstance(actual_sha, str):
            raise GitHubPullRequestError("GitHub reference response has no commit SHA")
        if actual_sha.lower() != expected_sha.lower():
            raise GitHubPullRequestError(
                "GitHub head branch does not match the expected commit"
            )

    async def _find_open(
        self,
        *,
        repository_path: str,
        owner: str,
        request: GitPullRequestRequest,
        headers: Mapping[str, str],
    ) -> GitPullRequestResult | None:
        response = await self._api_client.request(
            "GET",
            f"{repository_path}/pulls",
            headers=headers,
            query={
                "base": request.base_branch,
                "head": f"{owner}:{request.head_branch}",
                "state": "open",
            },
        )
        if response.status_code != 200:
            raise GitHubPullRequestError(
                f"GitHub list pull requests failed with status {response.status_code}"
            )
        if not isinstance(response.json_body, list):
            raise GitHubPullRequestError("GitHub pull request list response is invalid")
        if len(response.json_body) > 1:
            raise GitHubPullRequestError(
                "GitHub returned multiple matching open pull requests"
            )
        if not response.json_body:
            return None
        return _parse_pull_request(
            response.json_body[0],
            request=request,
            created=False,
        )


def _parse_github_repository(repository_url: str) -> tuple[str, str]:
    parsed = urlsplit(repository_url)
    if parsed.scheme not in {"https", "ssh"} or parsed.hostname != "github.com":
        raise ValueError("GitHub pull request repository must use github.com")
    if parsed.query or parsed.fragment or parsed.password is not None:
        raise ValueError("GitHub pull request repository URL is invalid")
    if parsed.scheme == "https" and parsed.username is not None:
        raise ValueError("GitHub pull request repository URL must not contain credentials")
    if parsed.scheme == "ssh" and parsed.username not in {None, "git"}:
        raise ValueError("GitHub pull request SSH user must be 'git'")
    parts = parsed.path.strip("/").split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("GitHub pull request repository path is invalid")
    owner, repository = parts
    repository = repository.removesuffix(".git")
    if any(
        not value
        or _REPOSITORY_PART.fullmatch(value) is None
        or value.startswith(".")
        for value in (owner, repository)
    ):
        raise ValueError("GitHub pull request repository path is invalid")
    return owner, repository


def _validate_branch(value: str) -> None:
    segments = value.split("/")
    if (
        not value
        or value.startswith(("-", "/"))
        or value.endswith(("/", "."))
        or "//" in value
        or ".." in value
        or "@{" in value
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
        or any(character in _FORBIDDEN_REF_CHARACTERS for character in value)
        or any(segment.startswith(".") or segment.endswith(".lock") for segment in segments)
    ):
        raise ValueError("GitHub pull request branch is invalid")


def _parse_pull_request(
    payload: object,
    *,
    request: GitPullRequestRequest,
    created: bool,
) -> GitPullRequestResult:
    value = _require_mapping(payload, "pull request")
    number = value.get("number")
    url = value.get("html_url")
    head = _require_mapping(value.get("head"), "pull request head")
    base = _require_mapping(value.get("base"), "pull request base")
    head_sha = head.get("sha")
    head_branch = head.get("ref")
    base_branch = base.get("ref")
    if not isinstance(number, int) or number <= 0 or not isinstance(url, str):
        raise GitHubPullRequestError("GitHub pull request identity is invalid")
    if (
        not isinstance(head_sha, str)
        or not isinstance(head_branch, str)
        or not isinstance(base_branch, str)
    ):
        raise GitHubPullRequestError("GitHub pull request branch response is invalid")
    if (
        head_sha.lower() != request.expected_head_sha.lower()
        or head_branch != request.head_branch
        or base_branch != request.base_branch
    ):
        raise GitHubPullRequestError(
            "GitHub pull request does not match the requested branches and commit"
        )
    return GitPullRequestResult(
        pull_request_id=str(number),
        url=url,
        head_sha=head_sha.lower(),
        head_branch=head_branch,
        base_branch=base_branch,
        created=created,
    )


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, dict) or not all(
        isinstance(key, str) for key in value
    ):
        raise GitHubPullRequestError(f"GitHub {name} response is invalid")
    return value
