import json
from collections.abc import Mapping
from types import TracebackType
from typing import Self

import httpx

from autoforge.infrastructure.git.github import (
    GitHubApiResponse,
    GitHubPullRequestError,
)


class GitHubApiTransportError(GitHubPullRequestError):
    pass


class HttpxGitHubApiClient:
    def __init__(
        self,
        *,
        timeout_seconds: float = 10.0,
        max_response_bytes: int = 1_048_576,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("GitHub API timeout_seconds must be positive")
        if max_response_bytes <= 0:
            raise ValueError("GitHub API max_response_bytes must be positive")
        self._max_response_bytes = max_response_bytes
        self._client = httpx.AsyncClient(
            base_url="https://api.github.com",
            follow_redirects=False,
            timeout=httpx.Timeout(timeout_seconds),
            transport=transport,
            trust_env=False,
        )

    async def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str],
        query: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
    ) -> GitHubApiResponse:
        normalized_method = method.upper()
        if normalized_method not in {"GET", "POST"}:
            raise ValueError("GitHub API method is not allowed")
        if (
            not path.startswith("/repos/")
            or "//" in path
            or "?" in path
            or "#" in path
        ):
            raise ValueError("GitHub API path is invalid")
        try:
            async with self._client.stream(
                normalized_method,
                path,
                headers=headers,
                params=query,
                json=json_body,
            ) as response:
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > self._max_response_bytes:
                        raise GitHubApiTransportError(
                            "GitHub API response exceeds the configured limit"
                        )
                status_code = response.status_code
        except httpx.TimeoutException:
            raise GitHubApiTransportError("GitHub API request timed out") from None
        except httpx.RequestError:
            raise GitHubApiTransportError("GitHub API transport request failed") from None
        try:
            payload: object = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise GitHubApiTransportError("GitHub API returned invalid JSON") from None
        return GitHubApiResponse(status_code=status_code, json_body=payload)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exception_type, exception, traceback
        await self.aclose()
