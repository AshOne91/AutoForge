import pytest

from autoforge.core.secret import SecretProvider, SecretReference
from autoforge.infrastructure.secret import (
    EnvironmentSecretNotFoundError,
    EnvironmentSecretProvider,
)


@pytest.mark.anyio
async def test_environment_provider_resolves_declared_reference_without_leaking_value() -> None:
    token = "github-token-never-log"
    provider: SecretProvider = EnvironmentSecretProvider(
        secret_names={"git/github/token": "AUTOFORGE_GITHUB_TOKEN"},
        environment={"AUTOFORGE_GITHUB_TOKEN": token},
    )

    value = await provider.resolve(SecretReference("git/github/token"))

    assert value.reveal() == token
    assert token not in repr(value)
    assert token not in str(value)


@pytest.mark.anyio
async def test_environment_provider_rejects_missing_mapping_and_value() -> None:
    provider = EnvironmentSecretProvider(
        secret_names={"git/github/token": "AUTOFORGE_GITHUB_TOKEN"},
        environment={},
    )

    with pytest.raises(EnvironmentSecretNotFoundError, match="value"):
        await provider.resolve(SecretReference("git/github/token"))
    with pytest.raises(EnvironmentSecretNotFoundError, match="reference"):
        await provider.resolve(SecretReference("git/github/other"))


def test_environment_provider_rejects_invalid_reference_mapping() -> None:
    with pytest.raises(ValueError, match="Secret reference"):
        EnvironmentSecretProvider(secret_names={" ": "AUTOFORGE_TOKEN"})
    with pytest.raises(ValueError, match="variable name"):
        EnvironmentSecretProvider(
            secret_names={"git/github/token": "autoforge-token"}
        )
