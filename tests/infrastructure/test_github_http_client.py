import json

import httpx
import pytest

from autoforge.core.git import GitPullRequestRequest
from autoforge.core.secret import SecretReference
from autoforge.infrastructure.git import (
    GitHubApiTransportError,
    GitHubPullRequestProvider,
    HttpxGitHubApiClient,
)
from autoforge.infrastructure.secret import InMemorySecretProvider

_TOKEN = "github-token-never-log"


@pytest.mark.anyio
async def test_client_serializes_relative_github_api_request() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"items": []})

    async with HttpxGitHubApiClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        response = await client.request(
            "GET",
            "/repos/example/repository/pulls",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            query={"base": "main", "state": "open"},
        )

    assert response.status_code == 200
    assert response.json_body == {"items": []}
    assert len(requests) == 1
    assert str(requests[0].url) == (
        "https://api.github.com/repos/example/repository/pulls?base=main&state=open"
    )
    assert requests[0].headers["Authorization"] == f"Bearer {_TOKEN}"


@pytest.mark.anyio
async def test_client_posts_json_without_following_redirects() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            302,
            headers={"Location": "https://example.invalid/token-target"},
            json={"message": "redirect"},
        )

    async with HttpxGitHubApiClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        response = await client.request(
            "POST",
            "/repos/example/repository/pulls",
            headers={"Authorization": f"Bearer {_TOKEN}"},
            json_body={"head": "autoforge/job-1", "base": "main"},
        )

    assert response.status_code == 302
    assert len(requests) == 1
    assert json.loads(requests[0].content) == {
        "head": "autoforge/job-1",
        "base": "main",
    }


@pytest.mark.anyio
async def test_client_redacts_transport_failures() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout(
            f"timed out with {_TOKEN}",
            request=request,
        )

    async with HttpxGitHubApiClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(GitHubApiTransportError, match="timed out") as caught:
            await client.request(
                "GET",
                "/repos/example/repository/pulls",
                headers={"Authorization": f"Bearer {_TOKEN}"},
            )

    assert _TOKEN not in str(caught.value)


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("content", "message"),
    (
        (b"not-json", "invalid JSON"),
        (b'{"value":"too-large"}', "configured limit"),
    ),
)
async def test_client_rejects_invalid_or_oversized_responses(
    content: bytes,
    message: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=content, request=request)

    limit = 8 if message == "configured limit" else 1_024
    async with HttpxGitHubApiClient(
        max_response_bytes=limit,
        transport=httpx.MockTransport(handler),
    ) as client:
        with pytest.raises(GitHubApiTransportError, match=message):
            await client.request(
                "GET",
                "/repos/example/repository/pulls",
                headers={},
            )


@pytest.mark.anyio
async def test_client_rejects_absolute_or_unscoped_paths_before_transport() -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={}, request=request)

    async with HttpxGitHubApiClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        for path in (
            "https://example.invalid/repos/example/repository/pulls",
            "/users/example",
            "/repos/example//pulls",
            "/repos/example/repository/pulls?token=unsafe",
        ):
            with pytest.raises(ValueError, match="path"):
                await client.request("GET", path, headers={})

    assert calls == 0


@pytest.mark.anyio
async def test_http_client_and_pull_request_provider_compose_end_to_end() -> None:
    methods: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        methods.append(request.method)
        if "/git/ref/" in request.url.path:
            return httpx.Response(200, json={"object": {"sha": "a" * 40}})
        if request.method == "GET":
            return httpx.Response(200, json=[])
        return httpx.Response(
            201,
            json={
                "number": 42,
                "html_url": "https://github.com/example/repository/pull/42",
                "head": {"ref": "autoforge/job-1", "sha": "a" * 40},
                "base": {"ref": "main"},
            },
        )

    async with HttpxGitHubApiClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        provider = GitHubPullRequestProvider(
            api_client=client,
            secret_provider=InMemorySecretProvider(
                {"git/github/token": _TOKEN}
            ),
        )
        result = await provider.create_or_get(
            GitPullRequestRequest(
                repository_url="https://github.com/example/repository.git",
                expected_head_sha="a" * 40,
                head_branch="autoforge/job-1",
                base_branch="main",
                title="Generate service",
                credential=SecretReference("git/github/token"),
            )
        )

    assert result.created is True
    assert result.pull_request_id == "42"
    assert methods == ["GET", "GET", "POST"]
