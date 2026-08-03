import asyncio

import pytest

from autoforge.core.secret import SecretProvider, SecretReference, SecretValue
from autoforge.infrastructure.secret import InMemorySecretProvider


def test_secret_value_redacts_string_and_repr() -> None:
    secret = SecretValue("super-secret-token")

    assert str(secret) == "***"
    assert repr(secret) == "SecretValue(***)"
    assert "super-secret-token" not in str(secret)
    assert "super-secret-token" not in repr(secret)
    assert secret.reveal() == "super-secret-token"


def test_in_memory_secret_provider_resolves_explicit_reference() -> None:
    async def scenario() -> None:
        provider: SecretProvider = InMemorySecretProvider(
            {"git/github/token": "secret-token"}
        )

        resolved = await provider.resolve(SecretReference("git/github/token"))

        assert resolved.reveal() == "secret-token"
        with pytest.raises(KeyError, match="was not found"):
            await provider.resolve(SecretReference("missing"))

    asyncio.run(scenario())
