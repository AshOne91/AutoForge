import asyncio
from pathlib import Path

from autoforge.core.git import GitCredentialReference
from autoforge.core.secret import SecretReference
from autoforge.core.workspace import Workspace
from autoforge.infrastructure.git.credential import git_credential_environment
from autoforge.infrastructure.secret import InMemorySecretProvider


def test_credential_helper_keeps_secret_out_of_files_and_cleans_up(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        token = "github-test-token-never-write"
        reference = GitCredentialReference(
            username="x-access-token",
            password=SecretReference("git/github/token"),
        )
        async with git_credential_environment(
            reference,
            secret_provider=InMemorySecretProvider(
                {"git/github/token": token}
            ),
            workspace=Workspace(tmp_path),
        ) as environment:
            helper = Path(environment["GIT_ASKPASS"])
            helper_root = helper.parent
            assert helper.is_file()
            assert environment["AUTOFORGE_GIT_PASSWORD"] == token
            assert environment["AUTOFORGE_GIT_USERNAME"] == "x-access-token"
            for path in helper_root.iterdir():
                assert token not in path.read_text(encoding="utf-8")

        assert not helper_root.exists()

    asyncio.run(scenario())
